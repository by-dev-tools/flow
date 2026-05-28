# Plan

## Current Focus

**PRs 1-3 + A-I all merged.** Plugin at **v1.2.4** on `main` (PR I squash `da0b2c4`). Consumer-feedback umbrella complete + FB-0010 consistency-discipline encoded + workflow-spawn-skip prevention in place + upgrade infrastructure docs live.

**PR J in flight** (`claude/youthful-chaum-500268`, off `main`) — **adversarial sharpening of the reviewer pipeline**, first of a research-grounded three-PR sequence (PR J = prompt-only sharpening, PR K = `/flow:red-team` skill + agent, PR L = trust-boundary detector + autonomous gate). Sources: deep research pass across frontier-lab official docs (Anthropic Claude Code best-practices, Multi-Agent Coordination Patterns, Claude Code Security, OpenAI CriticGPT, DeepMind CodeMender), AI-native production patterns (Anthropic's Code Review plugin, Cursor Bugbot, Cognition's read-only carve-out, GitHub Copilot CR), and academic literature on multi-agent debate / LLM-as-judge / self-critique. Convergent finding: Anthropic explicitly recommends "adversarial review step" with the over-engineering warning; CriticGPT-class research shows adversarial framing raises recall 16-93% on security-sensitive tasks; debate loops amplify bias (avoid); categorical schemas beat numeric scores. Bumps to **v1.2.5**.

PR J scope = prompt-only edits to four reviewer surfaces (auditor, plan-critic, lens-staff-engineer, security-review) + Anthropic's verbatim over-engineering warning at top of each prompt + prove-or-disprove self-check on auditor + plan-critic. Plan-critic also absorbs **PR-G FOLLOW-UP #5** (fan-out hunt vocabulary inside Internal incoherence). PR K adds `/flow:red-team` as a user-invocable standalone skill with threat-model categories + two-citation evidence + per-finding `Fix-confidence:` field (`AUTO-FIX-SAFE` vs `ESCALATE`) encoding the user's stated autonomy bar (FB-0011). PR L wires a mechanical trust-boundary detector into three workflow detection points (plan / staff-review / ship) with fall-through detection so missed signals at one point are caught at the next.

After PR J/K/L land: consumer install of v1.2.5+ across md-manager + health-tracker, begin active dogfood. Findings become PR H proper (the 11 remaining PR-G-review FOLLOW-UPs + PR-I review FOLLOW-UPs + PR-J/K/L-review FOLLOW-UPs + whatever new signal dual-project dogfood surfaces).

## Handoff Notes

- **PR I shipped** at squash `da0b2c4` on 2026-05-27; v1.2.4 workflow-spawn-skip prevention live.
- **PR H1 shipped** at squash `1a1cc12` on 2026-05-27; docs/upgrade.md + CHANGELOG.md live.
- **PR J prepared on `claude/youthful-chaum-500268`** — rebased on `origin/main` after collision with PR I (both bumping to v1.2.4 in parallel). Renumbered PR I → PR J + v1.2.4 → v1.2.5 + queued PR J → PR K + queued PR K → PR L. FB-0008 stale-base gate caught the collision pre-push (this is the gate doing exactly what it was designed to do).
- **PR K + PR L queued** behind PR J. PR K = `/flow:red-team` skill (standalone, mirrors security-review structure, FB-0008 stale-base preflight, FB-0006/FB-0007 source-file early-exit). PR L = trust-boundary detector (mechanical/regex, stdlib-only) + autonomous-invocation wiring + per-finding `AUTO-FIX-SAFE`/`ESCALATE` routing per FB-0011.
- **FB-0011 (autonomy bar) shipped in PR J** as the durable consumer-facing rule for autonomous-gate routing. Also saved to project memory at `~/.claude/projects/-Users-benyamron-dev-flow/memory/feedback_autonomy_bar.md` for cross-session reminder. Future autonomous gates default-to-ESCALATE; AUTO-FIX-SAFE category list starts conservative and grows only with dogfood evidence.
- **PR-G review FOLLOW-UPs:** PR-G #5 (plan-critic fan-out hunt) absorbed by PR J; 11 of the original 12 remain queued for PR H proper.
- **User-scope `~/.claude/settings.json` still has stale `extraKnownMarketplaces.llm-auditor`** key. Cosmetic; doesn't block.
- **Md-manager PR 5 (dogfood)** still pending; separate worktree.

## PR J — Adversarial sharpening of the reviewer pipeline (in flight, v1.2.4 → v1.2.5)

**Mode:** feature (prompt-only) | **Priority: high (research-grounded reviewer quality lift)**
**Goal:** Sharpen Flow's four reviewer surfaces along the dimensions deep research on adversarial review converges on, while encoding Anthropic's verbatim over-engineering warning to bound the false-positive tax. First of a three-PR sequence; PR K adds the `/flow:red-team` skill; PR L adds the autonomous gate.

**Scope (in):**
- `plugins/flow/agents/auditor.md` — new `## Principle` section (Anthropic's "flag only gaps that affect correctness or evidence-grounding" warning at principle level) + new `## Self-check before emitting` section (three-step disproof routine: name the specific session text that would invalidate the finding → re-scan for it → drop if found or fuzzy). Modeled directly on Anthropic's Claude Code Security "prove or disprove" pattern.
- `plugins/flow/agents/plan-critic.md` — same `## Principle` section adapted to the plan-vs-intent stance + new `## Self-check before emitting` (three-citation challenge variant — find a third citation that would resolve the apparent conflict). Also extends the `Internal incoherence` category to explicitly cover **fan-out contradictions within the plan** (count/name/slot/version referenced in N places where values disagree) — absorbs **PR-G FOLLOW-UP #5**.
- `plugins/flow/agents/lens-staff-engineer.md` — new `## How to read this diff` section (adversarial reading stance: "assume the diff is broken — what's the most likely break?") + the over-engineering warning. Composes with the existing FB-0010 silent-skip + fan-out hunts.
- `plugins/flow/skills/security-review/SKILL.md` — agent prompt at Step 3 shifts to **fully red-team identity** ("you are a red-team operator; your goal is to find an exploitable vulnerability"). "Hunt for:" → "Attack surface (categories to probe):" with each category gaining an attacker-mindset trailing question. New `Before emitting each BLOCKER/NIT` paragraph: trace the dangerous sink back to the input source; drop if not user-controllable in any realistic execution path. Output format gains "the attacker scenario in one sentence" on BLOCKER lines. **All operational logic preserved**: FB-0006/FB-0007 source-file early-exit, FB-0008 `[ -z ]` defaultBranch fallback chain discipline, FB-0009 fail-fast gh+jq, three-source diff capture.
- Version bump `1.2.4` → `1.2.5` in `plugins/flow/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (both fields: metadata + per-plugin). Descriptions refreshed; v1.2.4 workflow-spawn-skip summary moves to CHANGELOG history-of-record.
- `README.md` — "What v1.2.4 ships" → "What v1.2.5 ships". Skill catalog, agent count (8), rules count (4), slot count (16) all unchanged — no fan-out drift.
- `CHANGELOG.md` — new v1.2.5 entry placed above v1.2.4 entry, following Date / Version / Headline / 2-4 bullets / Breaking changes: none pattern.
- `dev-docs/feedback.md` — new **FB-0011** (autonomy bar — the durable consumer-facing rule the user stated mid-PR).
- `dev-docs/history.md` — `SAFETY`-marked entry (safety-critical files modified per `.claude/rules/safety.md`: auditor.md, plan-critic.md, security-review/SKILL.md).
- `dev-docs/plan.md` — this block + Current Focus refresh + Handoff Notes refresh + PR I block retitled to "merged."

**Scope (out):**
- **`/flow:red-team` skill + agent** — deferred to PR K.
- **Trust-boundary detector + autonomous-invocation wiring** — deferred to PR L.
- **`flow.config.json.trustBoundaryPatterns` schema slot** — deferred to PR L (lands paired with the detector per FB-0003 schema-pairing discipline).
- **Model-family routing across reviewers** — Claude Code subagent SDK substrate not there yet; roadmap follow-up.
- **Debate loop / cross-critique** — explicitly out per "Judging with Many Minds" (arxiv 2505.19477) bias-amplification finding. Parallel-then-merge stays.
- **Numeric 0-100 confidence scores** — explicitly out per OpenAI Cookbook (classifier 98% vs numeric 92-95%). Categorical schema preserved.
- **`dev-docs/spec.md` broadening** — queued hygiene PR; out of scope here.

**Spec-walk:**
- [x] `git log --oneline -5` precondition check ran on each safety-critical file (auditor.md, plan-critic.md, lens-staff-engineer.md, security-review/SKILL.md). No recent commits mention crash/safety/integrity/fallback; clean to edit.
- [x] `auditor.md` — `## Principle` and `## Self-check before emitting` sections added; categories untouched; footer + forbidden-phrases untouched; output schema unchanged.
- [x] `plan-critic.md` — `## Principle` and `## Self-check before emitting` added; `Internal incoherence` extended with fan-out clause; two-citation rule preserved (the fan-out clause uses it).
- [x] `lens-staff-engineer.md` — `## How to read this diff` added immediately after title intro; FB-0010 hunts intact; output format unchanged.
- [x] `security-review/SKILL.md` Step 3 — agent prompt switches to red-team identity; over-engineering warning added; attack-surface categories preserve all nine entries with added attacker questions; disprove paragraph added; BLOCKER line format gains attacker-scenario requirement. Steps 1, 2, 4, 5 untouched.
- [x] `plugins/flow/.claude-plugin/plugin.json` version 1.2.4 → 1.2.5; description refreshed.
- [x] `.claude-plugin/marketplace.json` metadata.version 1.2.4 → 1.2.5 (both metadata + per-plugin); both descriptions refreshed.
- [x] `README.md` "What v1.2.4 ships" → "What v1.2.5 ships".
- [x] `CHANGELOG.md` v1.2.5 entry added above v1.2.4 with date / headline / 5 bullets / Breaking changes: none.
- [x] `dev-docs/feedback.md` FB-0011 entry written.
- [x] `dev-docs/history.md` `SAFETY`-marked entry added; engineer-lens-dogfood NIT (FB-0008 mislabel) corrected; rebase + renumbering documented.
- [x] `dev-docs/plan.md` — this block + Current Focus refresh + Handoff Notes refresh.
- [x] Preflight: `claude plugin validate .` clean (sanity — no manifest schema changes, just version + description string edits).
- [x] Engineer-lens dogfood (parallel Agent invocation of the freshly-sharpened lens prompt against this PR's diff): 0 BLOCKER + 1 NIT (FB-0008 mislabel — fixed inline) + 1 FOLLOW-UP (phrasing precision — fixed inline). Meta-validation: the sharpened lens caught a real factual error in its own PR.
- [x] Existing eval fixtures pass: 5 passed / 0 failed / 3 skipped (pre-existing scaffold cases). No regression from the prompt edits.
- [x] FB-0008 stale-base preflight ran before push — caught the parallel PR I collision; rebased + renumbered cleanly.
- [ ] Self-fan-out grep post-rebase: no `v1.2.4` or `PR I` survivors in PR J's own content (CHANGELOG/history/plan v1.2.4 references are now ONLY about the merged PR I).
- [ ] `/flow:security-review` + `/flow:accessibility-review` final-pass: both will early-exit on this prompt-only diff (no source files beyond the 2 JSON manifests; no UI). Audit-trail STATUS: SKIPPED is the load-bearing artifact (per PR I discipline).
- [ ] Commit + push + `gh pr create` via the documented `/flow:ship` discipline (NOT direct `gh pr create` — PR I discipline applies here too).

**Confidence verdicts:**

**Assumption:** Prompt-only edits to reviewer system prompts are sufficient to operationalize the published research findings (adversarial framing, prove-or-disprove, over-engineering bound). No new agents, no new orchestration, no schema changes required.
**Confidence:** HIGH
**Why:** Anthropic's own Claude Code Security and Code Review plugin both encode this pattern at the prompt level, not in orchestration. The "evidence or silence" rule that Flow's reviewers already enforce composes naturally with the prove-or-disprove self-check. PR K adds new orchestration; PR J deliberately stays prompt-only to isolate the behavior change.
**If it flips:** Eval fixtures regress (existing borderline cases that were flagged on weak evidence now drop incorrectly). Tune the prove-or-disprove instructions or carve specific exclusions per category. Single-file fix per reviewer.

**Assumption:** Bundling PR-G FOLLOW-UP #5 (plan-critic fan-out hunt) into PR J doesn't expand scope meaningfully because plan-critic.md is already being edited for the prove-or-disprove section.
**Confidence:** HIGH
**Why:** One-line addition inside the existing `Internal incoherence` category description. No new category, no schema change. The two-citation rule applies unchanged. PR H proper's queue gets one item shorter.
**If it flips:** PR-G review caught more from FOLLOW-UP #5 than expected; carve out a separate PR. Low likelihood — the FOLLOW-UP entry itself says "one-line bullet under Internal incoherence."

**Files touched:** 10 — `plugins/flow/agents/auditor.md`, `plugins/flow/agents/plan-critic.md`, `plugins/flow/agents/lens-staff-engineer.md`, `plugins/flow/skills/security-review/SKILL.md`, `plugins/flow/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md`, `CHANGELOG.md`, `dev-docs/feedback.md`, `dev-docs/history.md`, `dev-docs/plan.md` (this file).

---

## PR I — Workflow-spawn prevention (merged, v1.2.3 → v1.2.4, squash `da0b2c4`)

**Mode:** feature (small) | **Priority: highest (pre-dogfood mechanical defense)**
**Goal:** Encode workflow-step discipline so future loops don't silent-skip the ship pipeline. User explicitly requested PR I after PR H1's review surfaced the issue + the "1 incident isn't usually enough threshold but the fix is trivially mechanizable" tradeoff was made explicit.

**Root cause analysis:** PR H1's actual skip wasn't "forgot to add `/flow:security-review` to the pipeline" — it was "bypassed `/flow:ship` entirely and ran `gh pr create` manually." `/flow:ship` already spawns security + a11y in Step 2. So the defense isn't "add more spawns to staff-review"; it's "make it harder to skip `/flow:ship` without noticing."

**Scope (in):** ← reduced from initial 12-file scope after observing audit/critique SKILL.md files end with rigid `## Output` blocks ("Do not add commentary before or after"). Adding "After this skill" footers there would conflict with the subagent output contract. Reduced scope keeps the footer addition tight to staff-review (the human-facing orchestration skill that's the natural pre-ship inflection point) + relies on workflow.md + `/flow:ship` Step 1.0 surface for the rest. Plan-critic Finding 1 REDIRECT confirmed this reduction.

- `plugins/flow/skills/staff-review/SKILL.md` — append "After this skill" footer naming `/flow:ship` (which spawns security + a11y automatically) as the canonical next step. Reframe the existing "ends with work ready, not merged" line into actionable forward motion. **Primary fix for the root cause.**
- `plugins/flow/skills/ship/SKILL.md` Step 1.0 — strengthen the assumption-surface block. Add `⚠️` per ASSUMES line + a new REMINDER paragraph naming the workflow-step silent-skip class explicitly + the "Always invoke /flow:ship, never `gh pr create`" rule. **Primary fix for the root cause.**
- `plugins/flow/docs/workflow.md` Step 10 — add an explicit "Never bypass `/flow:ship` with `gh pr create` directly" discipline. Names the failure mode: skipping `/flow:ship` skips the entire Step 2 (security + a11y reviews). **Primary fix.**
- `.claude/rules/general.md` (project-dev only — flow's own dev infra) — new "Workflow discipline" subsection: always invoke `/flow:ship` from this repo's `.claude/skills/ship`; never `gh pr create` directly. **Defense-in-depth for this repo's own development.**
- `CHANGELOG.md` — new v1.2.4 entry.
- `.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json` — v1.2.3 → v1.2.4 + description refresh.
- `dev-docs/history.md` — entry with SAFETY marker (manifest + ship/SKILL.md edits — both on safety paths list).
- `dev-docs/plan.md` — this block + mark FOLLOW-UP #20 done.

Plan-critic Finding 7 framing FOLLOW-UP: reviewer-footer is reframed above as "Primary fix"; staff-review IS the canonical inflection point where the workflow author chooses next-step, so the footer addresses the root cause directly. Workflow.md Step 10 + general.md are belt-and-suspenders.

**Scope (out):**
- Auto-spawn missing reviewers from `/flow:staff-review` (would need session-introspection helper; deferred per existing FOLLOW-UP).
- Pre-commit hooks (rejected: install friction; consistent with PR G decision).
- `/flow:upgrade` skill (FOLLOW-UP #15 — separate scope).
- README.md update (the existing version-log line just links to CHANGELOG.md per PR H1; no per-version inline entry needed).

**Spec-walk:**
- [ ] All 5 reviewer skills (`staff-review`, `critique-plan`, `audit-plan`, `audit-completion`, `log-disagreement`) have a uniform "After this skill" footer naming next step.
- [ ] `workflow.md` Step 10 has the explicit "never `gh pr create` directly" discipline.
- [ ] `/flow:ship` Step 1.0 assumption surface is visually louder (`⚠️` per line).
- [ ] `.claude/rules/general.md` has the new Workflow discipline subsection.
- [ ] CHANGELOG.md has a v1.2.4 entry; date matches the merge date; "Breaking changes: none" callout present.
- [ ] Both manifests bumped + descriptions refreshed.
- [ ] `claude plugin validate` clean.
- [ ] `/flow:doctor` Check 2.5 still emits expected output (12 historical-narrative WARN — unchanged on the current dev-docs/).
- [ ] Self-fan-out grep: no v1.2.3 references in v1.2.4-bumped descriptions; skill/agent/lens counts unchanged.
- [ ] **`/flow:security-review` + `/flow:accessibility-review` ARE spawned during this PR's review pipeline** (the meta-discipline — eat my own dog food). Per-diff gates will early-exit cleanly (no source/UI files in PR I diff — markdown + skill body edits only).
- [ ] `dev-docs/history.md` entry written with SAFETY marker.

**Confidence verdicts:**

**Assumption:** Per-skill exit reminders + workflow.md strictening will catch the workflow-spawn-skip class going forward without needing orchestration-level auto-spawn.
**Confidence:** MEDIUM
**Why:** Prompt-level reminders improve LLM behavior probabilistically. The exit-reminder is concrete enough that the next loop is likely to notice + act on it. Adversarial review + the FB-0010 lens hunt remain the backstop. If a 2nd workflow-spawn-skip incident occurs after PR I lands, that's the signal for orchestration-level auto-spawn (the harder fix).
**If it flips:** Promote to auto-spawn in `/flow:staff-review` Step N. Cost: session-introspection helper. Horizon: PR if/when triggered.

**Files touched:** 10 — `plugins/flow/skills/staff-review/SKILL.md`, `plugins/flow/skills/ship/SKILL.md`, `plugins/flow/docs/workflow.md`, `.claude/rules/general.md`, `CHANGELOG.md`, `README.md` (header rename only — `## What v1.2.3 ships` → `## What v1.2.4 ships`; caught by FB-0010 grep-first-edit-second pre-commit sweep), `.claude-plugin/marketplace.json`, `plugins/flow/.claude-plugin/plugin.json`, `dev-docs/history.md`, `dev-docs/plan.md`.

---

## PR H1 — Upgrade docs + CHANGELOG (in flight)

**Mode:** feature (small), docs-only | **Priority: highest (pre-install shore-up)**
**Goal:** Make the update workflow discoverable + auditable before consumer install. Two cheap fixes from the "is the update infrastructure solid?" Tier-2 audit — the rituals that prevent silent version drift between 2 active consumer projects.

**Scope (in):**
- New file: `docs/upgrade.md` — the 2-command update ritual (`/plugin marketplace update flow` → `/plugin install flow@flow` → `/flow:doctor`), when-to-run guidance, verification steps, troubleshooting (FB-0005 silent-failure mode, marketplace-key-mismatch, `/flow:doctor` Section 1 failures), optional auto-update opt-in with breaking-change warning.
- New file: `CHANGELOG.md` at repo root — extracted version-by-version from current README + history.md. Reverse chronological, one-liner per version + 2-3 bullets, breaking-change callouts (none yet). Replaces the inline "Versions:" block at the bottom of README.
- `README.md` — replace inline "Versions:" block with link to `CHANGELOG.md`; add cross-link to `docs/upgrade.md` in install + bootstrap sections so consumers can find it after first install.
- `docs/bootstrap.md` — add a "Keeping flow up to date" pointer to `docs/upgrade.md` at the end (after first PR walkthrough).
- `docs/migration.md` — same pointer (existing-project consumers also need to know).
- `dev-docs/history.md` — decision-log entry.
- `dev-docs/plan.md` — this block + Current Focus refresh.

**Scope (out):**
- **Version bump** — pure docs-at-root change; doesn't ship in plugin install (manifests unchanged); consumers reading on GitHub get the new docs without a re-install. Spares users a no-op upgrade ritual.
- **`minFlowVersion` slot + `/flow:doctor` Check 6** — deferred to PR H proper; mechanical defense for silent version drift, but ships best paired with the slot-count generalization (PR-G FOLLOW-UP #2).
- **Post-merge GitHub Actions reminder** — deferred; cheap when needed but assumes a feedback mechanism we don't have yet.
- **CHANGELOG auto-generation from history.md** — manual extraction this time; if drift becomes a maintenance burden, add a script later.

**Spec-walk:**
- [ ] `docs/upgrade.md` exists with: what-it-is, when-to-run, 2-command ritual, verification, troubleshooting (≥3 cases), auto-update note.
- [ ] `CHANGELOG.md` exists at repo root with v1.0.0 through v1.2.3 entries; reverse chronological; each entry has date + headline + 2-4 bullets + "breaking changes: none" or explicit list.
- [ ] `README.md` — inline "Versions:" block removed; replaced with one-line link to CHANGELOG.md; install section cross-references upgrade.md.
- [ ] `docs/bootstrap.md` + `docs/migration.md` — both have a one-line pointer to `docs/upgrade.md`.
- [ ] `claude plugin validate .` clean (no manifest changes; sanity).
- [ ] `/flow:doctor` Check 2.5 emits expected output: against flow's own tree, WARN with ~12 historical-narrative survivors in `dev-docs/history.md` + `dev-docs/feedback.md` + `dev-docs/handoffs/*` (intentional — those are accurate prose about past schema states, not stale current claims). Against a clean consumer project, PASS. Validated in both bash + zsh + sh (POSIX `set -- ; for; "$@"` pattern; an earlier `$SCAN_TARGETS` string-join silently no-op'd under zsh — yet another FB-0010 silent-skip caught at pre-commit).
- [ ] No version bump in either manifest; no v1.2.4 references anywhere.
- [ ] Self-fan-out grep: no contradictions introduced (CHANGELOG vs README vs history.md version notes match).
- [ ] `dev-docs/history.md` entry written (no SAFETY marker — no manifest/error-handling changes; verified against `.claude/rules/safety.md` `paths:` list — none of PR H1's 7 files match).
- [ ] CHANGELOG entries follow Keep-a-Changelog-style (Date + headline + bullets + "Breaking changes:" callout, no SHA/branch/tradeoffs blocks) — distinct from `dev-docs/history.md` format spec; the two intentionally diverge (CHANGELOG is consumer-facing terse, history.md is internal-tracking verbose).

**Confidence verdicts:**

**Assumption:** Pure docs-at-root changes don't need a version bump because they don't ship in the plugin install (consumers fetch them from GitHub, not via `/plugin install`).
**Confidence:** HIGH
**Why:** `docs/` is not packaged into the plugin binary — only `plugins/flow/*` ships. Consumers on v1.2.3 read the new docs from GitHub the moment we merge; no client-side action required. Spares a no-op `/plugin marketplace update`.
**If it flips:** A consumer reports they didn't NOTICE the new docs (they're delivered either way via GitHub, but the consumer's habit is to ignore unbumped versions). Bump to v1.2.4 then as a discoverability signal (not a delivery mechanism — the docs were already there). Single-file edit.

**Assumption:** CHANGELOG.md manual extraction matches the inline README version notes + history.md decisions without drift.
**Confidence:** MEDIUM
**Why:** Manual extraction from two sources risks scribal mismatch; FB-0010 specifically warns against this. Mitigation: I'll grep both sources after writing CHANGELOG and reconcile; the FB-0010 lens-engineer hunt + Check 2.5 will catch survivors at review.
**If it flips:** Lens-engineer flags fan-out between CHANGELOG and README. Fix inline before merge.

**Files touched:** 7 — `docs/upgrade.md` (new), `CHANGELOG.md` (new), `README.md`, `docs/bootstrap.md`, `docs/migration.md`, `dev-docs/history.md`, `dev-docs/plan.md`.

---

## PR G — Consistency discipline (FB-0010, in flight)

**Mode:** feature (small) | **Priority: highest**
**Goal:** Defend against the most-recurring bug class (FB-0010, 6 incidents): silent-skip on edge case + fan-out contradiction. Encode as explicit lens prompts + a mechanical doctor check + a workflow.md preflight note + a project-dev rule.

**Scope (in):**
- `dev-docs/feedback.md` — FB-0010 entry with all 6 PR citations and the two-flavor synthesis.
- `plugins/flow/agents/lens-staff-engineer.md` — silent-skip + fan-out hunts added to Hunts; consistency-sweep + silent-skip-sweep added to Specifically Asks; Gotchas reinforced.
- `plugins/flow/skills/doctor/SKILL.md` — Check 2.5 comparing `jq '.properties | keys | length'` on the schema against "N slots" claims in CLAUDE.md/README.md/docs/.
- `plugins/flow/docs/workflow.md` Step 4 — "consistency sweep" paragraph (FB-0010 reference).
- `.claude/rules/general.md` — Consistency discipline subsection (project-dev rule, auto-loads on every edit).
- `README.md` — v1.2.3 version note.
- `.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json` — v1.2.2 → v1.2.3, descriptions refreshed.
- `dev-docs/history.md` — decision-log entry.
- `dev-docs/plan.md` — this block + Current Focus refresh.

**Scope (out):**
- Pre-commit hooks (rejected: install friction outweighs benefit at this scale).
- Stop hook for skipped `/flow:critique-plan` (deferred to v1.x autonomous-routines work).
- Auto-fix for stale slot counts (doctor flags WARN; fix is author judgment).
- New eval fixtures (deferred until pattern proven by next consumer dogfood).

**Spec-walk:**
- [ ] FB-0010 entry exists with the two-flavor synthesis + all 6 PR citations.
- [ ] `lens-staff-engineer.md` Hunts list, Specifically Asks, and Gotchas all reference the new patterns explicitly.
- [ ] `/flow:doctor` Check 2.5 added; smoke against current flow repo emits PASS (all "16 slots" mentions match schema).
- [ ] `workflow.md` Step 4 mentions the consistency sweep.
- [ ] `.claude/rules/general.md` has the new subsection BEFORE "Autonomous work guardrails".
- [ ] README v1.2.3 line added.
- [ ] Both manifests bumped + descriptions refreshed; `claude plugin validate .` clean.
- [ ] `dev-docs/history.md` entry written.
- [ ] Self-test: grep for any remaining "14 slots" / "15 slots" / etc. across the tree returns nothing; no v1.2.2-only version strings in any new file.

**Confidence verdicts:**

**Assumption:** The lens-staff-engineer prompt addition will improve catch rate on the next consistency-class incident.
**Confidence:** MEDIUM
**Why:** Prompt-level vocabulary additions improve LLM behavior probabilistically. The shape is concrete enough (grep, then flag survivors) that the lens has a clear action to take. Adversarial review still serves as backstop.
**If it flips:** Promote to mechanical pre-commit check (rejected for v1.2.3 but reachable in v1.3+).

**Assumption:** Doctor Check 2.5's awk-filtered grep won't produce false positives on the current flow tree.
**Confidence:** HIGH
**Why:** Schema's slot count is THE source-of-truth and is single-pull-via-jq; any documented mismatch is genuinely stale. Verified via spec-walk smoke step.
**If it flips:** Tighten regex or add a doctor-skip glob slot. Single-file fix.

**Files touched:** 10 files (see Scope (in) — `.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json` count as 2 distinct edits even though the bullet groups them).

### PR H+ FOLLOW-UPs routed from PR G review pipeline (6 parallel lenses)

PR G's review (engineer + push-further + UX-designer + design-engineer + security + plan-critic) caught 2 BLOCKERs + 6 NITs (all fixed in-tree) + these 9 FOLLOW-UPs:

1. **FB-0010 Defense #4 — silent-skip skill-code pairing across existing shipped skills.** PR G covers defenses #1-3 (lens prompt + doctor check + project-dev rule); defense #4 (skill code: "pair every `2>/dev/null || true` / `// empty` / `|| ""` with explicit positive assertion or `[WARN]` branch") was not applied to existing skill bodies. Scope-deferred because the pattern requires a sweep of all 11 shipped skills + 5 scripts + 1 tool; bigger than PR G's small-feature charter. Owner: domain agent. Horizon: PR H (consumer-feedback round 2 after the new-project dogfood).

2. **Generalize Check 2.5 beyond slot count.** FB-0010 names 4 fan-out targets (counts, names, slots, version strings); Check 2.5 mechanizes only slot count. Symmetric pairs worth mechanizing: skill count (`ls plugins/flow/skills/ | wc -l` vs documented "N user-visible skills"), lens count (`ls plugins/flow/agents/lens-*.md` vs "four-lens"), rule count (`ls plugins/flow/rules/*.md` vs "four portable rules"). Each is ~5 lines of `ls | wc -l` + grep. Defer to v1.2.4 alongside next consumer dogfood. Owner: domain agent. Horizon: PR H.

3. **Consumer-shipped consistency rule (`plugins/flow/rules/general.md`).** PR G added the rule to project-dev `.claude/rules/general.md` only. The shipped portable rule (`plugins/flow/rules/general.md`) has no equivalent — consumers don't inherit the discipline at the rule-level. Lens-engineer catches it at staff-review time; a rule would catch it during execution. Cheap to land. Owner: docs agent. Horizon: PR H or v1.2.4.

4. **CLAUDE.md.template consumer-facing mention.** Consumers reading `template/base/CLAUDE.md.template` have no pointer to the consistency discipline (only `plugins/flow/docs/workflow.md` Step 4 surfaces it consumer-side). A one-line bullet would let consumers self-discover. Pairs naturally with #3. Horizon: PR H.

5. **`plugins/flow/agents/plan-critic.md` fan-out hunt addition.** Plan-critic's "Internal incoherence" category covers "plan steps that contradict each other" but lacks explicit fan-out vocabulary the way `lens-staff-engineer` now has. A plan listing "16 slots" in one section and "14 slots" in another is the in-plan analog of the same bug class. One-line bullet under Internal incoherence: "count/name/slot/version referenced multiple times in the plan — values must agree." Horizon: PR H.

6. **Schema-path fallback hardening in Check 2.5 (security).** When `CLAUDE_PLUGIN_ROOT` is unset, Check 2.5 falls back to `plugins/flow/schema/flow.config.schema.json` (project-relative). A malicious project shipping a same-named file under that path would have doctor report against the WRONG source-of-truth. No RCE, but "fails closed in wrong direction." Fix: require an explicit sentinel like `[ -f .claude-plugin/marketplace.json ]` before trusting the fallback path. Horizon: PR H or v1.2.4.

7. **Symlink-following grep hardening in Check 2.5 (security).** `grep -rEn` follows symlinks on BSD/macOS by default. A `docs/` symlinked to `/etc` would surface `/etc/*.md` "N slots" lines to doctor output (information disclosure, no exec). Defensive fix: `find … -type f -name '*.md' -print0 | xargs -0 grep …`. Horizon: PR H.

8. **Intra-file contradiction detection.** The PR F pass-2 doctor SKILL.md line 22 vs line 260 contradiction was a within-file fan-out shape. The lens-engineer's new hunt language is framed across-files; within-file is unmechanized. Worth a within-file consistency-sweep mode for the lens (or a new doctor check) once a 2nd within-file incident lands. Horizon: surfaces-when a second within-file incident lands.

9. **"PRs 1, B, D, E, F (×2)" citation drift across files.** The 6-incidents-across-5-PRs phrasing now varies across README, marketplace.json description, plugin.json description, FB-0010 entry, history.md, plan.md. Worth defining canonical phrasing in FB-0010 and reference-by-FB elsewhere ("see FB-0010 for the incident list"). This is itself a fan-out shape — ironic but real. Horizon: PR H.

10. **Re-open pre-commit-hook question if a 7th FB-0010 incident lands.** PR G explicitly rejected pre-commit hooks on install-friction grounds. The rejection is defensible only if the prompt-level + check-level defenses suffice. The 7th incident is the experimental signal. Trigger: any future PR that ships a stale count/name/slot/version that survives both `lens-staff-engineer` and Check 2.5. Horizon: triggered-by-occurrence; route to v1.3 if/when.

11. **Workflow.md Step 4 placement of non-mechanical disciplines.** Step 4's lead sentence says "Mechanical gates that MUST be green." Both the existing "Failure-pattern memory" paragraph and PR G's new "Consistency sweep" paragraph are non-mechanical disciplines living inside the "mechanical gates" step. Design-engineer flagged the structural drift but the in-tree fix (sub-heading or move-to-Step-6) was deferred to avoid scope creep in PR G. Horizon: next workflow.md-touching PR.

12. **"Consumer-shipped" vs "project-dev" terminology standardization.** FB entries use parenthetical labels; history.md uses "Two-layer defense" framing. Worth a style-guide note for future FB entries that span both surfaces. Horizon: dev-docs hygiene PR.

13. **Release tagging + version-pinning recipe** (caught during PR H1 pre-lens self-check). PR H1's first draft of `docs/upgrade.md` included a "Pin to a prior version" recipe using `git checkout v1.2.3` — but flow doesn't tag releases at the git-tag level (only `pre-flow-plugin` tag exists). And `~/.claude/plugins/flow/` isn't a known stable path across Claude Code install shapes. Recipe was removed from upgrade.md as false-affordance per CLAUDE.md "no false affordances" rule; recipe re-introduction requires (a) backfill-tagging v1.0.0..v1.2.3 against historical merge SHAs (one-time), (b) auto-tag-on-merge for future PRs (GitHub Actions step on main push or release-please-style automation), (c) verify the actual Claude Code plugin install dir convention. Owner: docs+infra. Horizon: PR H proper or v1.2.4 if a consumer hits a regression they need to roll back from.

14. **CHANGELOG drift trigger** (PR H1 push-further-lens NIT). Manual CHANGELOG maintenance assumed by PR H1 has no mechanical trigger. Add `/flow:ship` spec-walk item: "if version bumped in this PR, CHANGELOG.md has a new entry for the bumped version." Either as a `/flow:ship` Step N check, or as a pre-commit grep in the project's preflight. Until then, the first forgotten CHANGELOG update IS the test of discipline. Horizon: PR H proper or any `/flow:ship`-touching PR.

15. **`/flow:upgrade` skill** (PR H1 push-further-lens FOLLOW-UP). Wraps the 2-command ritual + runs `/flow:doctor` + diffs CHANGELOG-since-last-installed-version. ~40 lines of bash; 1-2 hour build. Real ambition rightly deferred from PR H1 (which is docs-only); land alongside `minFlowVersion` slot + Doctor Check 6 (FOLLOW-UP #2). Horizon: PR H proper or v1.2.4.

16. **CLAUDE.md "Product Principles" should anchor the patch-additive discipline** (PR H1 push-further-lens BLOCKER-lite, addressed in-tree by softening CHANGELOG + upgrade.md prose). The discipline ("patch bumps aim to be additive") now lives in CHANGELOG + upgrade.md but is not in CLAUDE.md, plugin.json description, or any process gate. Worth promoting to CLAUDE.md "Product Principles" as a stated discipline (not contract). Horizon: next CLAUDE.md-touching PR.

17. **Historical-narrative immunity for Check 2.5** (PR H1 engineer-lens FOLLOW-UP). Check 2.5 currently flags every "N slots" mention where N != schema-actual, including legitimate historical prose like "schema bumped from 13 to 16" in `dev-docs/history.md`. The current flow tree emits WARN with 12 such survivors — all intentional narrative. Fix shape: either (a) add a `dev-docs/handoffs/` + `dev-docs/history.md` exclude-list to Check 2.5 (cheap, blunt), (b) skip lines containing context-words like `was`, `bringing`, `estimated`, `→`, `from N` (heuristic), or (c) require a sentinel `<!-- historical -->` HTML comment to mark intentional historical-narrative lines (explicit, more work for authors). Land alongside the Check 2.5 generalization to skill/lens/rule counts (FOLLOW-UP #2) so consumers don't get spurious WARNs on their own historical narrative. Horizon: PR H proper or v1.2.4.

18. **`docs/README.md` index** (PR H1 UX/design-engineer FOLLOW-UP). With `docs/` now holding 4 substantive files (bootstrap, migration, first-pr, upgrade) plus CHANGELOG.md at root, the implicit user journey isn't obvious from the directory listing. A ~20-line decision-tree index ("new project → bootstrap; existing → migration; already installed → upgrade; first PR → first-pr") would be a 5-minute fix compounding across consumer projects. Horizon: PR H proper.

19. **CHANGELOG framing softening** (PR H1 UX/design-engineer NIT). History.md describes CHANGELOG as "Keep-a-Changelog-style" but it lacks K-a-C's `[Unreleased]`, `Added/Changed/Fixed/Removed/Security` subhead categories, and the keepachangelog.com footer link. Honesty fix: change framing in history.md + (eventually) CHANGELOG header from "Keep-a-Changelog-style" to "flow's own consumer-changelog format (date + headline + bullets + breaking-change callout)." Cheap; ride next history.md-touching PR.

21. **`PreToolUse` hook on `Bash` matching `gh pr create`** (PR I push-further-lens FOLLOW-UP F2). Currently PR I ships 3 prompt-level reminders to use `/flow:ship` instead of `gh pr create`. Three of the four defenses (Step 1.0 surface, staff-review footer, workflow.md Step 10) only render if the author opens `/flow:ship` or `/flow:staff-review` — the author who skips both still skips silently. A PreToolUse hook in `.claude/settings.json` matching `gh pr create` could print "use /flow:ship; remove this hook from .claude/settings.json if intentional." ~10 lines of settings.json + 1 doc paragraph. Higher signal-to-friction than another prompt reminder. Horizon: triggered by 2nd workflow-spawn-skip incident OR ride next `.claude/settings.json`-touching PR.

22. **Consumer-shipped workflow rule (`plugins/flow/rules/workflow.md`)** (PR I push-further-lens FOLLOW-UP F3). PR I adds the workflow discipline to `.claude/rules/general.md` (project-dev only). Push-further correctly noted my "fan-out avoidance" reasoning was backwards — rules auto-load on every edit, workflow.md auto-loads on zero edits; the rule is the load-bearing surface and the doc is the reference. Consumer projects need the same defense. Cheap to add — copy the `.claude/rules/general.md` Workflow discipline subsection into a new `plugins/flow/rules/workflow.md` with `paths: ['**/*']` frontmatter. Horizon: PR H proper or v1.2.5.

23. **Encode-after-1-incident threshold as a written rule** (PR I push-further-lens FOLLOW-UP F1). PR I's history.md "Lessons learned" names the principle: *"threshold isn't hard; it's 'is encoding cost less than expected recurrence cost?'"* Should be promoted out of one PR's history entry into `.claude/rules/general.md` (or `dev-docs/feedback.md` as a meta-rule). Otherwise the next 1-incident "but the fix is cheap" judgment call has no precedent to lean on. Cheap; ride next feedback-touching PR.

24. **Make STATUS: SKIPPED actually load-bearing** (PR I push-further-lens FOLLOW-UP B1's path-2 deferral). PR I softened the language ("explicit log line in the session transcript" — true) from "load-bearing audit trail" (false; nothing programmatically consumes the STATUS lines). The real fix: either append STATUS lines to a per-PR record under `~/.claude/plugins/data/flow/` OR add a `/flow:doctor` Check that scans the most recent session transcripts for the STATUS lines. Real scope; defer until the discipline surface needs the upgrade. Horizon: when audit-trail consumption becomes a concrete need.

25. **`.claude/rules/documentation.md` plan.md-maintenance rule vs PR-I practice** (PR I UX/design-engineer NIT #3). The rule says "Completed items move to 'Recently Completed'" but PR I marked FOLLOW-UP #20 in-place with `✅ SHIPPED in PR I (v1.2.4)` prefix because the numbered list is referenced from history.md ("FOLLOW-UP #20"); moving items would break the cross-refs. Resolution: update the documentation rule to explicitly permit in-place `✅ SHIPPED in PR X` marking for numbered traceability lists (numbered FOLLOW-UPs, FB-XXXX entries). Cheap; ride next `.claude/rules/documentation.md`-touching PR.

26. **/flow:ship Step 1.0 surface is now ~25 lines** (PR I engineer-lens FOLLOW-UP F2). Originally 3 ASSUMES lines. PR I adds 7 lines of REMINDER prose. 2.3x expansion. If the user ignored 3 lines, will they read 25? Signal-to-watch at next dogfood. Not fix-now; capture for next /flow:ship-touching PR's plan.

20. ✅ **`/flow:security-review` + `/flow:accessibility-review` workflow-spawn discipline** — **SHIPPED in PR I (v1.2.4).** PR H1's workflow loop spawned plan-critic + 4 staff-review lenses but DID NOT spawn `/flow:security-review` + `/flow:accessibility-review`. Skipped by author judgment ("they'd early-exit on docs-only anyway"). User caught: "were the ship reviews run?" — they hadn't been. **This is itself the FB-0010 silent-skip class applied to workflow discipline (not code).** The 9th FB-0010 incident, and a new sub-class (workflow-step-skip vs code-edge-skip). Per workflow.md Step 10 (the "Never bypass `/flow:ship`" subsection added by PR I — formerly framed under Step 6 in pre-PR-I plan prose) + FB-0008/FB-0033, the discipline is to ALWAYS spawn the reviewers — they produce a `STATUS: SKIPPED` log line in the session transcript as evidence the discipline ran, NOT silent-skip the spawn itself. Make-good: ran both retroactively (security: STATUS SKIPPED no source/config in diff; a11y: STATUS SKIPPED no UI in diff). Defense: `/flow:ship` Step 1.0 already prints the workflow-step assumption surface (which lists security/a11y). Strengthen that surface to either (a) auto-spawn the reviewers if missing or (b) require an explicit author confirmation that they ran. Owner: domain. Horizon: PR H proper or next `/flow:ship`-touching PR. Promote at next /flow:ship feedback synthesis since this is now a 3rd-time-recurring discipline shape: PR F-pass-1 (gawk-only awk = portability silent-skip), PR H1 zsh-vs-bash (word-splitting silent-skip), PR H1 workflow-spawn-skip (judgment silent-skip).

---

## PR E+ follow-ups from PR D review

PR D's lens dogfood (staff-engineer + security combined) caught 2 BLOCKERs + 2 NITs (all fixed in-tree) + 2 FOLLOW-UPs routed here:

1. **Structured exit-status marker for `/flow:*review` early-exit vs clean-run.** PR D's early-exit uses `exit 0` + a `STATUS: SKIPPED — ...` stdout line as a soft marker. When `/flow:ship` Step 2 invokes the reviewers via `Skill('flow:security-review')`, the orchestrator can't programmatically distinguish "skipped — no source files" from "ran, no findings." Both are exit 0. A structured final-line marker (`STATUS: SKIPPED` / `STATUS: CLEAN` / `STATUS: FINDINGS`) would let `/flow:ship` audit-trail what actually ran. PR D adds the `STATUS: SKIPPED` line in the early-exit path; symmetric `STATUS: CLEAN` / `STATUS: FINDINGS` for the substantive paths is the v1.3+ enhancement. Owner: domain agent. Horizon: PR E or post-extraction.

2. **Pattern-injection RCE confirmed safe (informational, no action).** PR D security lens explicitly verified that `grep -E "$PATTERN"` from a flow.config.json-sourced regex does NOT have command-injection surface — `grep` treats the arg as a POSIX ERE, not a shell expression; shell metas land as regex metachars or grep fails outright. Per FB-0004 trust model (flow.config.json = project-owned, package.json-tier trust), this is the correct posture. Captured here as audit-trail evidence; no code change.

---

## PR D+ follow-ups from PR C review

PR C's lens dogfood (staff-engineer + push-further combined) caught 1 BLOCKER + 2 NITs (all fixed in-tree) + 1 FOLLOW-UP routed here:

1. **Surface-AFTER variant of `/flow:ship` Step 1.0 workflow-step assumption block.** PR C ships the surface-BEFORE form (informational pre-flight; zero new infrastructure, prints what's ASSUMED to have run). The richer signal — what ACTUALLY ran — would come from a post-ship "Workflow steps actually executed this session" summary derived from session-transcript scan. Higher-signal than surface-before but requires session-introspection helper that doesn't exist yet. Ship the cheap form (PR C); add this as a v1.3+ enhancement when a session-introspection helper lands. Owner: domain agent. Horizon: post-extraction v1.3.

### Additional FOLLOW-UPs from PR C **full-review re-pass** (4-parallel lens spawn matching the canonical /flow:staff-review pattern)

Per user direction, ran the canonical 4-parallel pattern (engineer + push-further + security + plan-critic + audit-completion) instead of the combined-lens shortcut used in the initial PR C review. Caught 1 BLOCKER + 1 NIT + 2 MEDIUM (audit) — all fixed inline — plus 4 new FOLLOW-UPs:

2. **Single-principle "skips compound" preamble in workflow.md** (push-further roadmap-concrete). PR C adds "even on docs-only ones" qualifier at Step 2 AND Step 6 — both restate the same FB-0008/FB-0033 lesson. A single principle near the top (e.g., a "Discipline" preamble after the 11-step list) cited from Step 2 + 6 would be tighter and prevent the next docs-only qualifier (security, a11y, ship-spike) from spawning a third copy. Horizon: next workflow.md-touching PR.

3. **Cross-repo provenance one-liner inside /flow:ship Step 1.0 emitted block** (push-further roadmap-concrete). Current block cites "FB-0033-style discipline" only in the prose AROUND the verbatim emit. Surfacing "(dogfood-driven: md-manager FB-0033 + flow FB-0008)" inside the printed block would let consumers know this is real burned-cost lesson, not arbitrary nagging. Reduces "why is this here" friction. Horizon: same as #2.

4. **Stacked-PR plan-noting convention** (plan-critic INTERNAL-INCOHERENCE FOLLOW-UP). When PRs chain off each other for review (B branched off A; C off B; D off C; E off D), the per-PR plan's "Files touched" list will appear to mismatch the actual PR diff (which contains stacked content from earlier PRs in the chain). Future stacked-PR plans should note "this is the C slice of a stacked A+B+C PR" so reviewers can map the file list correctly. Horizon: convention update in workflow.md or plan-template; trigger on next stacked-PR sequence.

5. **`/plugin marketplace list` output-shape eval test** (audit-completion MEDIUM #2). The `^flow` anchor in PR C's verify recipe depends on marketplace-list outputting names at column 0 with no leading bullet/indent/glyph. Today's behavior matches; a Claude Code version change could break it silently. Add a regression fixture under `plugins/flow/evals/security/test_marketplace_list_format.py` paralleling the existing fixture shape — assert that `claude --print "/plugin marketplace list" 2>&1 | head -5` returns names at column 0 (or the test fails with a clear "output format changed; update bootstrap.md grep recipe" message). Cheap; one-shot. Bootstrap.md now documents this assumption inline so consumers can adjust without grepping the eval. Horizon: PR D or E.

---

## PR C+ follow-ups from PR B review

PR B's Phase 7 dogfood (staff-engineer + simplify + security combined lens against the stale-base preflight implementation) caught 2 BLOCKERs + 2 NITs (all fixed in-tree) + 1 FOLLOW-UP routed here:

1. **Eval fixture for the stale-base gate.** Test cases: (a) current branch passes silently; (b) stale branch blocks with expected stderr + exit 1; (c) no `refs/remotes/origin/HEAD` configured + no `flow.config.json` → resolves to literal `main`; (d) `flow.config.json.defaultBranch = "trunk"` + no remote HEAD → resolves to `"trunk"`. Both empirical-smoke cases (c) + (d) were verified manually during PR B Phase 9 iteration, but no regression fixture protects them. Would have caught both BLOCKERs PR B's lens flagged (empty-DEFAULT_BRANCH degenerate; cross-shell variable scope). Owner: testing agent. Horizon: PR C or D. Place under `plugins/flow/evals/security/test_stale_base_check.py` paralleling the existing `test_cwd_constraint.py` + `test_malicious_config.py` shape (assert-on-exit-code + assert-on-stderr).

---

## PR 4+ follow-ups from PR 3 review

PR 3's Phase 7 dogfood (3 parallel lens agents — engineer+simplify combined + push-further + security; skipped UX-designer + design-engineer + accessibility with reason: doc/template surface, no UI) caught 4 BLOCKERs + 9 NITs + 4 FOLLOW-UPs. BLOCKERs + NITs fixed in-tree. FOLLOW-UPs routed here:

1. **Preflight script library across 3 stacks** (engineer FOLLOW-UP). web/check.mjs and tauri/check.mjs share ~80% structure (`loadConfig`, `runGate`, GATES summary, exit-code handling). A shared helper module would let stack-specific gates be the diff. Defer to a "preflight library" PR if/when a 4th stack lands; today the divergence is borderline. Owner: domain agent. Horizon: when adding stack #4 (rust-only, python, go) OR when an existing stack's preflight needs a behavior change that has to land in all three.

2. **`$comment-*` keys in flow.config.json.example are janitorial overhead** (push-further inline-cheap, deferred for design discussion). Replacing them with a sibling `flow.config.example.md` cheat-sheet was suggested. Counter-argument: putting docs in a separate file means the consumer holds two files in their head during bootstrap. Hold the existing pattern until PR 4 dogfood confirms or refutes the friction. If md-manager's PR 4 agent flags it, redesign in v1.3.

3. **Collapse bootstrap's 6 steps to 4** (push-further inline-cheap, deferred for design discussion). Merging install+copy and verify+smoke-PR was suggested. Today the 6-step shape mirrors what an adopter actually does (each step has a different verification). PR 4 dogfood will surface whether the step count feels heavy in practice.

4. **Ship `template/bootstrap.sh` shim** (push-further inline-cheap, deferred for design discussion). One-command bootstrap (`./bootstrap.sh --stack web` does Steps 2+3 in one invocation) was suggested. Real value, but the cp ladder doubles as documentation of WHAT the script would do. v2.0+ roadmap already lists `/flow:init` skill as the canonical answer; ship the shim ALONGSIDE that work to avoid two scaffolding paths competing.

5. **Swift preflight unquoted `$WORKSPACE_OR_PROJECT` word-split** (security NIT). `WS=$(ls *.xcworkspace | head -n1)` then used unquoted via shellcheck-disable so xcodebuild gets two args. Filename with space breaks; filename with shell metas could in theory exec. Repo-owner-controlled, so not a real attack surface. Fix: use bash array `WS_ARGS=(-workspace "$WS")` then `xcodebuild "${WS_ARGS[@]}"`. Horizon: PR 4 or when first swift consumer touches the file.

---

## PR 3+ follow-ups from PR 2 review

PR 2's Phase 7 dogfood (4 parallel lens agents + security review on PR 2's own diff) caught 2 BLOCKERs + 11 cheap NITs (all fixed in-tree) + 8 FOLLOW-UPs (routed here):

1. **Eval coverage for cwd-constraint rejection path** (security lens). `extract_session.py`'s `allow_external_paths=False` default needs a regression fixture covering (a) symlink resolution under cwd, (b) `..` glob expansion, (c) absolute `--reference-paths` rejection, (d) `--allow-external-paths` opt-out. The constraint is a 30-line block in a 600-line file; future refactor could regress it silently. Owner: testing agent. Horizon: next reviewer-touching PR (could land in PR 3 or as a quick follow-up flow PR). Add fixtures under `plugins/flow/evals/fixtures/cwd-constraint/`.

2. **Eval fixture for malicious-flow.config.json injection probe** (security lens). The `jq -r` + quoted-args pattern in skill `!<cmd>` blocks is correct today, but no fixture asserts that `flow.config.json` with shell metas in `referenceGlob`, `defaultBranch`, `typecheckCmd` is handled without command execution. One-line test would prevent silent regression. Horizon: PR 3.

3. **Memory tool `validateMemoryDir` should `realpath` before prefix check** (security lens). Currently `Path.resolve()` collapses `..` but doesn't follow symlinks. Limited threat surface today (script only LISTS filenames; doesn't read contents). Revisit when `check.mjs` ever starts reading entry contents. Recommended fix when revisited: `realpathSync` before `startsWith(projectsRoot + '/')` check.

4. **Single-source slot documentation** (push-further roadmap-concrete). Slot semantics duplicated across `flow.config.schema.json` (description fields), `workflow-help/SKILL.md` (slot table), `plugins/flow/docs/workflow.md` (slot table), and per-skill "Config slots used" tables. Will drift the first time a slot's behavior changes and someone updates 3 of 4. Pick schema as canonical; generate the others at release time, OR replace prose tables with a one-line pointer. Horizon: v1.2.

5. **Loud-warning copy deduplication** (UX lens FOLLOW-UP). The `⚠️ flow.config.json.<slot> not set; ...` string appears verbatim in 5 skills. If wording evolves (e.g., add schema link), it's 5 edits. Extract to a single doc snippet referenced by `${CLAUDE_PLUGIN_ROOT}/docs/...`. Horizon: v1.2.

6. **workflow-help vs README cheat-sheet duplication** (UX lens FOLLOW-UP — recurring; PR 1 review flagged the same shape for README+workflow.md). Workflow-help SKILL output overlaps the README cheat-sheet. Confirm side-by-side; decide canonical surface (probably README points at `/flow:workflow-help`, since the latter substitutes resolved project context). Horizon: next docs-touching PR.

7. **workflow-help craft asymmetry vs flow's own preached doctrine** (push-further EXPLORATION). The plugin asks consumers to hold themselves to "uncommon care" but its own front door (`/flow:workflow-help`) is "comprehensive reference." Could be a one-line aphorism per step, a "what flow gives you / what flow asks of you" contract, or similar. Surfaces when: anyone edits `plugins/flow/skills/workflow-help/SKILL.md` or `plugins/flow/docs/workflow.md`.

8. **Fallback message tone for missing project docs** (UX lens EXPLORATION). All 5 review skills emit `(no spec doc at $SPEC)` etc. when a doc is missing. Reads like shell output. Friendlier shape might be `Spec doc: not configured — set flow.config.json.specPath to enable spec-grounded review`. Surfaces when: a consumer reports the messages feel cryptic, OR when adding a new review skill (rule the tone in then).

## Per-stack memory-tool foreign-cwd verification

Routed for **PR 4 dogfood** (md-manager extraction umbrella): the `check.mjs` `deriveMemoryDir()` falls back to `~/.claude/projects/<slug-of-cwd>` when no project-name match exists under `~/.claude/projects/`. For consumers using flow at user-scope from a cwd that doesn't match any existing slug, this creates a separate memory dir per worktree — which the harness won't auto-load. Already documented in pr2-flow-plan.md's confidence verdict; surface as a real follow-up entry once md-manager PR 5 dogfoods.

## PR 2 follow-ups from PR 1 review

The walk-through-the-loop review on PR 1 surfaced two findings that are out-of-scope for PR 1 but in-scope for PR 2. Quoted here verbatim so PR 2's planner doesn't have to re-derive them:

1. **Consumer-vs-flow path divergence in critique-plan default.** `plugins/flow/skills/critique-plan/SKILL.md:13` hardcodes `--reference-glob "core-docs/*.md"`. When flow runs `/flow:critique-plan` on itself (which uses `dev-docs/` not `core-docs/`), the plan-critic sees zero reference docs. The fix is a `flow.config.json.referenceGlob` slot that the SKILL reads at invocation, with the documented default chain (consumer projects: `core-docs/*.md`; flow's own repo: `dev-docs/*.md`). PR 2's `flow.config.schema.json` work picks this up. Cost: ~10 min once the config-slot machinery exists.

2. **`extract_session.py --reference-paths` accepts arbitrary host paths.** Currently, `gather_reference_docs` reads any absolute path the caller passes; output is injected verbatim into the auditor subagent's context. In the current invocation chain, the caller is the `critique-plan` SKILL with a hardcoded glob, so consumer input never reaches it. But if a future skill or recipe ever forwards user-controlled paths, an attacker could exfil file contents (e.g., `~/.ssh/config`) into the subagent's prompt and out via tool output. Constrain to `cwd` (reject resolved paths outside `Path.cwd()`) unless an explicit override flag says otherwise. Document the trust model in the script docstring. Pairs naturally with PR 2's path-validation rule baseline (`plugins/flow/hooks/default-hooks.json`).

## Active Work Items

### Consumer-feedback follow-ups (PRs A-E, sequential) — driven by md-manager PR 4 report 2026-05-25

5 small focused PRs absorbing md-manager's first-real-consumer dogfood findings. FB-0005 through FB-0009 + 1 EXPLORATION (rule-of-three close-out skill) captured in PR A's intake. Each PR runs the workflow loop (plan → execute → preflight → /flow:staff-review or lens emulation → /flow:ship pipeline → open PR; user merges).

**Canonical priority sequence + one-liner per PR:** see [`dev-docs/roadmap.md`](roadmap.md) § Now. The per-PR plans below carry the detailed scope, spec-walk, and confidence verdicts; roadmap.md is the single source of truth for "what's the order + what's next."

#### PR A — Consumer feedback intake (docs-only; in flight on `pr-a/consumer-feedback-intake`)

**Mode:** feature (small)
**Goal:** Capture md-manager's PR 4 consumer-feedback report as canonical flow `dev-docs/` artifacts before any implementation work begins. Closes the cross-repo signal loop (consumer flagged → captured → addressable).

**Scope (in):**
- Create `dev-docs/roadmap.md` with format header + Now / Next / Later / § Exploration sections. Flow has been deferring this since v1.0.0; right moment to land it (matches the consumer-template convention flow ships in PR 3).
- Add 5 FB entries to `dev-docs/feedback.md` (FB-0005 through FB-0009) covering the 5 rough edges from the consumer report. Each entry: source, what-was-said, synthesized rule, applies-to, validation.
- Add 1 EXPLORATION entry to `dev-docs/roadmap.md` § Exploration covering the rule-of-three `flow:close-out` skill abstraction observation (don't extract yet — wait for a fourth instance).
- Update plan.md: Current Focus advances to "PRs A-E sequenced"; Handoff Notes refreshed for post-PR-3 state; PR A-E Active Work Item block added.

**Scope (out):** Any code changes to plugin artifacts (PR B+ does that). The Workflow discipline lesson from md-manager FB-0033 (workflow.md should reinforce "don't skip even on docs-only") routes to PR C, not PR A.

**Spec-walk:**
- [ ] `dev-docs/roadmap.md` exists with the 4-section structure (Now / Next / Later / § Exploration) + the rule-of-three EXPLORATION entry.
- [ ] `dev-docs/feedback.md` has 5 new entries (FB-0005 through FB-0009) per the documentation rule schema; each cites the consumer report as source.
- [ ] `dev-docs/plan.md` Current Focus + Handoff Notes reflect the new state; PR A-E block added under Active Work Items.
- [ ] No edits to `plugins/flow/*`, `template/*`, `docs/*`, `evals/*` (verify via `git diff --name-only origin/main..HEAD` returning only `dev-docs/` paths).
- [ ] `claude plugin validate .` exits clean (sanity).

**Confidence verdicts:**

**Assumption:** Creating `dev-docs/roadmap.md` now (rather than deferring to a "roadmap initialization" PR) is the right moment because PR A has a real EXPLORATION entry to land + flow has been deferring this since v1.0.0 with no cost.
**Confidence:** HIGH
**Why:** Empty roadmap.md would be busy-work; one with a real entry is canonical reference material.
**If it flips:** EXPLORATION moves to `dev-docs/plan.md` "Backlog" section instead. Single-file revert.

**Assumption:** FB-0005 through FB-0009 numbering doesn't collide with any in-flight session writing to feedback.md.
**Confidence:** HIGH
**Why:** Single-author repo; no in-flight concurrent FB-writing session.
**If it flips:** Renumber at commit time; non-architectural.

**Risks:** none material — purely additive docs.

**Files touched:** `dev-docs/roadmap.md` (new), `dev-docs/feedback.md` (5 entries added), `dev-docs/plan.md` (Current Focus + Handoff Notes + new Active Work Item block).

#### PR B — Stale-base preflight in `/flow:ship` Step 1 (queued)

**Mode:** feature (small) | **Priority: highest**
**Goal:** Add a mechanical preflight check that prevents the stale-base BLOCKER class md-manager PR 4 burned 4 lens spawns surfacing. FB-0008 captures the rule + pattern.

**Scope (in):** `plugins/flow/skills/ship/SKILL.md` Step 1 — add `git fetch origin --quiet` + `git merge-base --is-ancestor` check; exit 1 with clear stderr message if branch is behind. Mirror same check into `/flow:ship-spike` Step 1 and `/flow:staff-review` Step 1 (both also diff-vs-default-branch consumers).

**Scope (out):** Auto-rebasing on detection. Stale-base detection is the gate; the fix is the user's call.

**Spec-walk:**
- [ ] All 3 skills (`ship`, `ship-spike`, `staff-review`) have the stale-base check at Step 1, before any expensive operation.
- [ ] Check uses `flow.config.json.defaultBranch` with 3-tier fallback chain (matches PR 1 locked idiom).
- [ ] `git fetch origin --quiet` precedes the check (otherwise it tests against a stale local view).
- [ ] Error message names the gap (`(current HEAD: X; base needs N commits)`) so the user knows what's needed.
- [ ] `claude plugin validate .` clean.
- [ ] Smoke test: forge a stale branch in `/tmp/`; verify `/flow:ship` exits 1 with the expected message.

**Confidence verdicts:**

**Assumption:** Forced-update / shallow-clone consumers won't hit false positives from the `merge-base --is-ancestor` check.
**Confidence:** HIGH
**Why:** `git fetch origin` brings the remote ref current; `is-ancestor` is the standard idiom. Shallow clones fail-soft (no ancestry info = treats as ancestor).
**If it flips:** Add `--depth=1` aware fallback (`git rev-parse origin/<branch> 2>/dev/null` first). Surface at smoke time.

**Files touched:** `plugins/flow/skills/{ship,ship-spike,staff-review}/SKILL.md`.

#### PR C — Marketplace install verification + `/flow:ship` assumption surfacing (queued)

**Mode:** feature (small) | **Priority: high**
**Goal:** Two related fixes pairs into one PR. Address FB-0005 (marketplace-key-mismatch install docs gap) by adding a verification step to `docs/bootstrap.md` + `docs/migration.md`. Address the workflow discipline lesson (md-manager FB-0033 cross-project applicability) by making `/flow:ship` print which workflow steps it assumes have already run.

**Scope (in):**
- `docs/bootstrap.md` Step 1 + `docs/migration.md` Stage 1: add `/plugin marketplace list | grep '^flow'` verification step after install, with fallback instruction to re-run `/plugin marketplace add by-dev-tools/flow` if absent. Document the rename-causes-stale-key class of issue.
- `plugins/flow/skills/ship/SKILL.md` Step 1: print "ASSUMES: /critique-plan ran during plan; /simplify ran post-commit; /flow:staff-review ran with substantive output or explicit N/A per lens. Skips become visible at the next ship." Single-line; doesn't gate, just surfaces.
- `plugins/flow/docs/workflow.md` Step 6 + Step 2 sub-step: add "even for docs-only diffs" qualifier per workflow discipline (a) recommendation from the consumer report.

**Scope (out):** A `flow:doctor` skill (deferred; workflow discipline (b)). The doc fix + assumption-surfacing is enough behavior change to test the discipline; doctor is v1.2+ if discipline doesn't change.

**Spec-walk:**
- [ ] `docs/bootstrap.md` + `docs/migration.md` have the marketplace-name verification step at install-time.
- [ ] `plugins/flow/skills/ship/SKILL.md` Step 1 prints the workflow-step assumption list.
- [ ] `plugins/flow/docs/workflow.md` Step 6 + Step 2 have the "even for docs-only" qualifier.
- [ ] `claude plugin validate .` clean.

**Files touched:** `docs/bootstrap.md`, `docs/migration.md`, `plugins/flow/skills/ship/SKILL.md`, `plugins/flow/docs/workflow.md`.

#### PR D — Per-diff non-UI early-exit (paired in `/flow:security-review` + `/flow:accessibility-review`) (queued)

**Mode:** feature (medium) | **Priority: medium**
**Goal:** Pair FB-0006 + FB-0007. Both reviewers should detect "no relevant files in diff" at Step 1 and early-exit cleanly, saving spawn cost on docs-only PRs.

**Scope (in):**
- `plugins/flow/skills/security-review/SKILL.md` Step 1: add per-diff source-file detection (`git diff <base>..HEAD --name-only | grep -E ...`). If empty, emit "[security-review] no source/config files in diff; skipping." and exit 0.
- `plugins/flow/skills/accessibility-review/SKILL.md` Step 1: add per-diff UI-file detection, AND in addition to the existing `uiSurface=false` project-wide gate. Same shape as security-review.
- `plugins/flow/schema/flow.config.schema.json`: add two optional slots (`sourceFilePatterns`, `uiFilePatterns`) for projects with non-standard file layouts (e.g., monorepos). Defaults documented inline.
- `plugins/flow/.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`: bump metadata.version + plugin version to v1.2.1 (additive patch — no breaking changes). Update description text to reflect the new slot count (14 → 16) + the per-diff early-exit behavior.

**Scope (out):** Restructuring the reviewers to take diff-paths as inputs (today they read from disk; the early-exit checks the path list but the reviewer itself still works as-is).

**Spec-walk:**
- [ ] Both reviewers' Step 1 has per-diff detection wired.
- [ ] Schema has 2 new slots with defaults + examples; consumers exist (the reviewer skills read them).
- [ ] No false-positive on a real source-touching PR (smoke: stage a single `src/foo.ts` edit; verify both reviewers proceed without early-exit).
- [ ] Manifest version + slot count reflected (note: doesn't necessarily bump major.minor; this is a 1.2.x patch since it's additive).
- [ ] `claude plugin validate .` clean.

**Files touched:** `plugins/flow/skills/{security-review,accessibility-review}/SKILL.md`, `plugins/flow/schema/flow.config.schema.json`, `.claude-plugin/marketplace.json`, `plugins/flow/.claude-plugin/plugin.json`.

#### PR E — `gh` CLI fail-fast check (queued)

**Mode:** feature (small) | **Priority: low**
**Goal:** FB-0009. Add `command -v gh` check at `/flow:ship` Step 1, `/flow:staff-review` Step 1, `/flow:ship-spike` Step 1. Emit install hint + exit 1 if absent rather than exit 127 at invocation site.

**Scope (in):**
- 3 SKILL.md edits adding the `command -v gh` check.
- `docs/bootstrap.md` Step 1 + `docs/migration.md` Stage 1: document `gh` as a prerequisite alongside `claude` + `node` + `jq`.

**Spec-walk:**
- [ ] All 3 skills' Step 1 has the gh-CLI check.
- [ ] Install hint message includes both macOS (`brew install gh`) and the generic URL.
- [ ] Both bootstrap + migration docs name `gh` in the prereq list.
- [ ] `claude plugin validate .` clean.

**Files touched:** `plugins/flow/skills/{ship,staff-review,ship-spike}/SKILL.md`, `docs/bootstrap.md`, `docs/migration.md`.

---

### PR 3 — Template directory + bootstrap docs + absorb PR-2 follow-ups (SHIPPED — awaiting merge)

**Mode:** feature
**Branch:** `pr3/template-directory` (off `main` after PR 2 squash `3409103`)
**Goal:** Ship the consumer-side scaffolding so a new project can adopt flow in ~10 minutes per `docs/bootstrap.md`. Cover the three stacks documented in the umbrella plan (web / swift / tauri-rust-ts). Provide `docs/migration.md` for existing projects (md-manager being the upcoming case in PRs 4-6). Absorb PR 2's two follow-up eval fixtures (cwd-constraint + malicious-config injection) since PR 3 is touching the eval surface anyway. Manifest bump v1.1.0 → v1.2.0.

**Scope (in):**
- `template/base/` — Tier 1 (required: CLAUDE.md.template, flow.config.json.example, .claude/settings.json.example, .claude/rules/safety.md.template, README.md.template, .gitignore.template) + Tier 2 (recommended-but-shippable-empty: core-docs/{spec,plan,roadmap,history,feedback}.md scaffolds with format headers).
- `template/stacks/web/` — Vite/React/TS stack: `tools/preflight/check.mjs` (npm typecheck + build + test), `.claude/skills/link/SKILL.md` (vite dev server), `.claude/rules/{ui,dev-server}.md`, `.github/workflows/ci.yml` (Node CI), `.gitignore.append` (web-stack entries).
- `template/stacks/swift/` — `tools/preflight/check.sh` (xcodebuild + xcodebuild test + swift-format lint), `.claude/rules/safety.md.append` (.xcodeproj/.xcworkspace edits), `.github/workflows/ci.yml` (macOS runner + Xcode action), `.gitignore.append` (DerivedData, xcuserdata).
- `template/stacks/tauri-rust-ts/` — `tools/preflight/check.mjs` (npm typecheck + build + cargo fmt --check + cargo clippy -D warnings + cargo test), `.claude/skills/link/SKILL.md` (tauri dev), `.claude/rules/ui.md`, `.github/workflows/ci.yml` (Node + Cargo), `.gitignore.append` (target/, src-tauri/target).
- `docs/bootstrap.md` — step-by-step adoption for a NEW project (per stack: which template/base files to copy, which stack overlay to merge, how to fill placeholders, how to install plugin, how to validate `flow.config.json`).
- `docs/migration.md` — adoption for an EXISTING project with `.claude/` content (md-manager case): the additive-then-replace pattern, what to keep project-shaped (safety.md, ui.md, link/, project skills) vs delete (workflow skills, generic rules, planner+docs, memory tool).
- PR-2 FOLLOW-UPs absorbed:
  - `plugins/flow/evals/fixtures/cwd-constraint/` — fixtures covering symlink-into-cwd (accepted), `..` glob expansion (rejected), absolute `--reference-paths` (rejected with explicit stderr), `--allow-external-paths` opt-out (accepted). Wire into `evals/run_evals.py` or add a separate `evals/run_security_evals.py` if the existing harness shape doesn't fit security-class tests.
  - `plugins/flow/evals/fixtures/malicious-config/` — fixture: `flow.config.json` with shell metas in `referenceGlob`, `defaultBranch`, `typecheckCmd`. Asserts no command execution; values land as opaque strings into their consumer skills.
- Manifest bump in both `.claude-plugin/marketplace.json` (metadata.version + plugin version) and `plugins/flow/.claude-plugin/plugin.json`: 1.1.0 → 1.2.0. Description updated to mention "template directory + bootstrap docs."

**Scope (out):**
- md-manager-side changes (PRs 4-6).
- Other PR-2 FOLLOW-UPs not tagged for PR 3 (items 3-8 in the FOLLOW-UPs section above stay deferred).
- `/flow:init` auto-bootstrap skill (v2.0+ per post-extraction roadmap).
- v1.x+ post-extraction features.

**Locked patterns from PR 1 + PR 2 (still binding):**
- Templates use `{{PLACEHOLDER}}` syntax for fill-in slots (CLAUDE.md.template, README.md.template, safety.md.template).
- All shell command examples in template files use `sh -c "$VAR"`, never `eval "$VAR"`.
- Per-stack preflight scripts print loud `⚠️` warnings for any unset config slot, never silently no-op.
- Default-branch resolution in template-shipped scripts uses the 3-tier fallback chain.
- Cross-file refs in template SKILL.md files (only `link/` ships in templates) use `${CLAUDE_PLUGIN_ROOT}` ONLY for plugin-shipped paths; consumer-side relative paths are fine.
- No md-manager-specific tokens in template artifacts.

**Phased execution (each ends with one commit; per-phase verifiable success criteria):**

- **Phase 1 — Plan + consumer-model read.** Read schema (13 slots, defaults). Survey md-manager (the reference web consumer) for actual npm scripts, settings.json shape, .gitignore. Done. **Success:** schema slots enumerated; web-stack defaults validated against md-manager actuals.
- **Phase 2 — `template/base/` (Tier 1 + Tier 2).** 8 files. **Success:** all 8 files exist; placeholders use `{{NAME}}` syntax consistently; flow.config.json.example parses with jq; settings.json.example parses; no md-manager tokens.
- **Phase 3 — 3 stack overlays.** ~15 files total. **Success:** each stack has at least preflight + CI workflow + .gitignore.append; preflight scripts have node --check / shellcheck clean (where applicable); CI yamls parse with yq/python-yaml.
- **Phase 4 — `docs/bootstrap.md` + `docs/migration.md`.** **Success:** bootstrap covers all 3 stacks; migration explicitly names the keep-vs-delete file lists matching the md-manager spec; both docs reference template paths that exist.
- **Phase 5 — Absorb 2 PR-2 FOLLOW-UPs.** **Success:** cwd-constraint fixture rejects out-of-cwd path with non-zero exit + explicit message; malicious-config fixture asserts shell-meta values pass through as strings; both wired into the eval harness.
- **Phase 6 — Bootstrap verification.** In `/tmp/`, follow `docs/bootstrap.md` for the web stack from scratch. Optional smoke for swift + tauri (full bootstrap may need a real Mac/Rust env). **Success:** web bootstrap produces a working project with `claude --plugin-dir <flow> --print "/flow:workflow-help"` returning the expected output; `claude plugin validate` clean against the bootstrapped project.
- **Phase 7 — Dogfood PR 3 via `/flow:staff-review` + `/flow:security-review`.** Skills exist on main now (PR 2 shipped them). Spawn lens agents via Agent tool with `subagent_type: lens-*`. Triage; apply BLOCKER + cheap NIT inline; route FOLLOW-UPs. **Success:** at least 3 of 4 lenses ran (a11y likely skipped via uiSurface=false); all BLOCKERs fixed; FOLLOW-UPs routed.
- **Phase 8 — `/flow:ship` + manifest bump + open PR.** Run the pipeline; bump to v1.2.0; verify md-manager spec accuracy (no changes expected — PR 3 is consumer-side); push; open PR; never merge. **Success:** PR open against main; MERGEABLE; PR body documents 8 phases; md-manager spec re-verified.

**Confidence verdicts:**

- **Three stack overlays are sufficient for v1.2.0 coverage.** HIGH. Web + swift + tauri match the umbrella's stated targets. Other stacks (python, go, rust-only) defer to v1.3+.
- **`docs/bootstrap.md` is testable from scratch in `/tmp/` for the web stack.** HIGH. Node + npm are universally available.
- **Swift + tauri bootstrap verification may be smoke-only** (no full Xcode/Rust env in this session). MEDIUM. Mitigation: document the assumption in the bootstrap docs; consumer reports become PR 3+ FOLLOW-UPs.
- **PR-2 FOLLOW-UP eval fixtures slot cleanly into the existing harness.** MEDIUM. The existing `evals/run_evals.py` runs against jsonl session fixtures for the auditor; security-class tests (assert-no-shell-execution) need a different shape. Likely add a separate `evals/run_security_evals.py` (or skip the harness wiring and ship as standalone Python smoke tests under `evals/fixtures/cwd-constraint/test.py`). Decide at Phase 5.
- **Manifest bump to v1.2.0 is additive (no breaking changes).** HIGH. Templates are consumer-pulled, not plugin-pushed.

**Risks:**
- Stack-overlay scope creep — keep each overlay to ~5 files, defer "everything a stack might need" to consumer fork.
- Migration doc accuracy depends on md-manager's actual state at PR 4 time — keep it general where possible, point at md-manager-pr4-6-spec.md for specifics.
- Bootstrap verification in `/tmp/` requires `claude` CLI access from the shell — confirmed available (used in PR 1 + PR 2 smoke tests).

**Files touched (anticipated):**
- New under `template/base/`: 8 files (Tier 1 + Tier 2)
- New under `template/stacks/web/`: 5 files
- New under `template/stacks/swift/`: 4 files
- New under `template/stacks/tauri-rust-ts/`: 5 files
- New under `docs/`: `bootstrap.md`, `migration.md`
- New under `plugins/flow/evals/fixtures/`: 2 fixture dirs (cwd-constraint, malicious-config)
- Modified: `.claude-plugin/marketplace.json`, `plugins/flow/.claude-plugin/plugin.json` (v1.2.0); `dev-docs/{history,plan,feedback}.md` (Phase 8 synthesis); possibly `plugins/flow/evals/run_evals.py` or new `evals/run_security_evals.py`.

### PR 2 — Workflow surface backfill (SHIPPED — awaiting merge)

**Mode:** feature
**Branch:** `pr2/workflow-backfill` (off `docs/pr2-handoffs`)
**Canonical plan:** [`dev-docs/handoffs/pr2-flow-plan.md`](handoffs/pr2-flow-plan.md). 8 phases, per-phase verifiable success criteria, 6 confidence verdicts, 6 risks, ~24 files. User direction: execute autonomously, self-grade against success criteria, follow the workflow being implemented at each stage.

**Phase 1 status (complete):** all 12 md-manager sources fetched to `/tmp/pr2-sources/` (sizes match estimates ±2%). Source-read observations refining the handoff plan:
- Staff-review extraction (Phase 3-4): md-manager uses `subagent_type: Explore` with inline prompts; PR 2 changes to `subagent_type: lens-*` with extracted agent files. Structural change confirmed MEDIUM. Fallback documented.
- Security/a11y reviews: heavier md-manager-specific token references than handoff anticipated (`--sand-9`, `--page-text-quiet`, "markdown-notes app"). De-projection effort scaled accordingly.
- All 4 skills start step numbering at 0 (same off-by-one PR 1's `/flow:ship` had). Apply PR-1 NIT fix (start at 1) across all ports.
- `ship-spike` references non-existent `tools/preflight/check.mjs` — port keeps as a config-slot opportunity (consumer-side preflight is project-specific per consolidation doc Decision 1).

Execution proceeds through Phases 2-8 per the handoff.

### PR 1 — Flow plugin restructure + initial workflow surface (SHIPPED — awaiting merge)

Status: all spec-walk checkboxes complete; PR opened at [by-dev-tools/flow#5](https://github.com/by-dev-tools/flow/pull/5); walk-through-the-loop review pass surfaced 3 BLOCKERs + 2 cheap NITs, all fixed in follow-up commit `65a0a58`; plan-critic retroactive verdict APPROVED; recovery anchor at git tag `pre-flow-plugin`. Full history entry in `dev-docs/history.md`. Original plan spec-walk preserved below for reference.

---

**Mode:** feature

**Goal:** Move existing root-level plugin content into `plugins/flow/*`, rename `llm-auditor` / `assumption-auditor` identifiers to `flow` (both marketplace name and plugin name), bump to v1.0.0, add `/flow:ship` skill (ported from md-manager via the locked /ship port table — 3a/3b split, loud-warning pattern, default-branch discovery, config-slot doc paths) and `plugins/flow/docs/workflow.md` (canonical 11-step loop, de-projected), rename this repo's `core-docs/` to `dev-docs/` to match the consumer-vs-plugin convention. The result is an installable v1.0.0 `flow` plugin whose marketplace shape matches Anthropic's pattern and whose own dev-tracking is cleanly separated from the plugin artifacts it ships.

**Scope (in):**
- Create recovery tag `pre-flow-plugin` against current HEAD (`8857ebd`) and push it. Brief calls this the recovery anchor; it doesn't exist yet.
- Restructure plugin artifacts via `git mv` (preserve history):
  - `agents/{auditor,plan-critic}.md` → `plugins/flow/agents/`
  - `skills/{audit-plan,audit-completion,critique-plan,log-disagreement}/SKILL.md` → `plugins/flow/skills/`
  - `scripts/{extract_session,bounding_logic,log_disagreement}.py` → `plugins/flow/scripts/`
  - `evals/{ground_truth.yaml,run_evals.py,fixtures/}` → `plugins/flow/evals/`
  - `DISAGREE.md` → `plugins/flow/DISAGREE.md`
- Rename `.claude-plugin/marketplace.json`: marketplace `name` `llm-auditor` → `flow`; plugin `name` `assumption-auditor` → `flow`; plugin `source` `./` → `plugins/flow`; add `metadata.pluginRoot: "./plugins"`; update `homepage`/`repository` URLs to `https://github.com/by-dev-tools/flow`; bump marketplace `metadata.version` and plugin `version` to `1.0.0`; expand `description` to reflect the workflow scope.
- Rename `.claude-plugin/plugin.json`: `name` `assumption-auditor` → `flow`, `version` `0.3.0` → `1.0.0`, `homepage`/`repository` URLs to by-dev-tools/flow, updated `description` covering the audit/critique + workflow surface.
- Move `.claude-plugin/plugin.json` to `plugins/flow/.claude-plugin/plugin.json` (Anthropic pattern: marketplace at repo root, plugin manifest inside its own directory).
- Update `plugins/flow/scripts/log_disagreement.py` disagreement-storage path: `~/.claude/plugins/data/assumption-auditor/disagreements/` → `~/.claude/plugins/data/flow/disagreements/`. Note: pre-existing user data at the old path becomes orphaned (acceptable — it's local dev/debug data; called out in PR body and README).
- Add `plugins/flow/skills/ship/SKILL.md` — port from md-manager `.claude/skills/ship/SKILL.md` (fetched via `gh api repos/by-dev-tools/md-manager/contents/...`) per the locked PR-1 /ship port table:
  - Steps 0, 2, 4–5: port as-is.
  - Step 1 (`/security-review`, `/accessibility-review`): `[PR 1 LIMITATION]` placeholder block; skills land in PR 2.
  - Step 3a (user-feedback → `feedback.md`): port active — pure markdown, no tooling dep.
  - Step 3b (memory machinery via `tools/memory/check.mjs`): `[PR 1 LIMITATION]` placeholder; memory tooling lands in PR 2.
  - Step 6 (`gh pr create --base main`): replace hardcoded `main` with default-branch discovery (`git symbolic-ref` → `flow.config.json.defaultBranch` slot → literal `main` fallback).
  - Step 7 (`/link`): replace with generic "if your project has a dev-server skill, invoke it now" note.
  - `npm run typecheck` references: config-slot via `flow.config.json.typecheckCmd`; **loud warning** if unset (`⚠️ flow.config.json.typecheckCmd not set; skipping preflight re-run. Set this slot to enable typecheck on /ship.`) — never silent no-op.
  - Doc paths (`core-docs/history.md`, etc.): config-slot via `flow.config.json.historyPath` / `planPath` / `roadmapPath` / `feedbackPath` / `specPath` with sensible defaults.
  - De-project: strip md-manager-specific tokens (`src/store.tsx`, `--sand-*`, `Geist`, `Mini`, `pattaya`, etc.).
- Add `plugins/flow/docs/workflow.md` — port from md-manager `core-docs/workflow.md` (already fetched at `/tmp/md-workflow.md`):
  - Strip md-manager-specific examples (designer cargo gates, md-manager preflight lists, etc.).
  - Annotate `/simplify`, `/batch`, `/debug`, `/loop`, `/claude-api` as **"(bundled with Claude Code)"** wherever referenced — they are Anthropic-native, not flow-provided.
  - Annotate `/critique-plan`, `/audit-plan`, `/audit-completion` as **flow-internal** (not an external assumption-auditor plugin anymore — they're bundled into flow).
  - Add a "Project config slots" section narratively documenting `flow.config.json` (paths, defaultBranch, typecheckCmd, etc.). JSON Schema lands PR 2.
  - Add a "Bootstrap status" / "v1.0.0 scope" section: only `/flow:ship` + the four audit/critique skills + 2 agents (`auditor`, `plan-critic`) shipped; full workflow surface comes in PR 2.
- Rename `core-docs/` → `dev-docs/` (flow's own dev-tracking; per Decision 4 + the consumer-vs-plugin convention). Move all files: `plan.md` (this plan + prior content preserved), `history.md`, `feedback.md`, `spec.md`, `workflow.md`. Note: this is a `git mv` rename, not a content rewrite.
- Update `CLAUDE.md` (project-dev concern, not plugin-shipped) for the new layout: plugin artifacts at `plugins/flow/*` (not root); project-dev knowledge at `dev-docs/` (not `core-docs/`); identity is "flow" (not "assumption-auditor"); call out the `template/core-docs/` (consumer-side) vs `dev-docs/` (plugin-side) distinction explicitly so future sessions don't conflate them.
- Update `.claude/rules/safety.md`: rewrite path references for the new layout. Safety-critical paths become `plugins/flow/agents/auditor.md`, `plugins/flow/scripts/extract_session.py`, `plugins/flow/scripts/bounding_logic.py`, `plugins/flow/skills/audit-plan/SKILL.md`, `plugins/flow/skills/audit-completion/SKILL.md`, `plugins/flow/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `plugins/flow/evals/run_evals.py`, `plugins/flow/evals/ground_truth.yaml`. (Plus add `plugins/flow/skills/ship/SKILL.md` to the safety-critical list — it's new published surface.)
- Update `.claude/rules/general.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md` (project-dev infra): any references to `core-docs/...` get updated to `dev-docs/...`.
- Rewrite root `README.md` for the marketplace-shaped identity: what the marketplace is (`flow`), how to install (`/plugin marketplace add by-dev-tools/flow && /plugin install flow@flow`), pointer to `plugins/flow/docs/workflow.md` for what the plugin does, v1.0.0 status (audit/critique + `/flow:ship` shipped; rest of workflow surface lands PR 2; template directory lands PR 3), History section referencing the `pre-flow-plugin` tag for archeology and noting the rename from `llm-auditor`. The pre-rename assumption-auditor README content is preserved at the tag — not lost.
- Manual cold-read of full diff with security + simplification + project-agnostic lenses (the plugin's own `/flow:simplify` doesn't exist — `/simplify` is bundled-native, can be used; flow's `/flow:staff-review` doesn't exist yet — bootstrap exception per the brief).
- Per-phase commits with `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer.
- Open PR against `main`; user merges.

**Scope (out):**
- Workflow skills `/flow:staff-review`, `/flow:security-review`, `/flow:accessibility-review`, `/flow:ship-spike`, `/flow:workflow-help` — PR 2.
- Agents `planner`, `docs`, the four staff-review lens agents (`staff-engineer`, `ux-designer`, `design-engineer`, `push-further`), optional `uncommon-care` — PR 2.
- Rules `general.md`, `plan-discipline.md`, `documentation.md`, `exploration.md` (the project-dev ones at `.claude/rules/*` that would become plugin-shipped portable rules) — PR 2.
- `tools/memory/check.mjs` — PR 2.
- `plugins/flow/schema/flow.config.schema.json` — PR 2.
- `plugins/flow/hooks/*` — PR 2.
- `template/` directory (web / swift / tauri-rust-ts overlays + `template/base/`) — PR 3.
- Backfilling `/flow:ship`'s PR-1-limitation placeholders — PR 2.
- Any md-manager-side changes (config layer, dogfood, deletion of duplicates) — PRs 4–6.
- Updating `~/.claude/settings.json` (`assumption-auditor@llm-auditor` → `flow@flow`) — user-side one-liner after merge; flagged in PR body.
- v1.x+ post-extraction features (autonomous routines, JTBD substrate, visual artifacts, design lenses) — out of the extraction umbrella entirely.

**Spec-walk checkboxes** (each binds to a verification step):

- [ ] `pre-flow-plugin` tag exists on `origin` and points at the pre-PR-1 HEAD (`git ls-remote --tags origin | grep pre-flow-plugin` matches `8857ebd`).
- [ ] All plugin artifacts live under `plugins/flow/` (verify: no `agents/`, `skills/`, `scripts/`, `evals/`, `DISAGREE.md` at repo root; all six moved).
- [ ] `.claude-plugin/marketplace.json` parses with `jq .` and declares marketplace `name: "flow"` + plugin `name: "flow"` + plugin `source: "plugins/flow"` (or equivalent `pluginRoot`-relative form).
- [ ] `plugins/flow/.claude-plugin/plugin.json` parses with `jq .` and declares `name: "flow"`, `version: "1.0.0"`, by-dev-tools/flow URLs.
- [ ] `plugins/flow/skills/ship/SKILL.md` exists, contains the explicit `[PR 1 LIMITATION]` placeholder for `/security-review` + `/accessibility-review`, contains the loud-warning string for unset `typecheckCmd`, has no md-manager-specific tokens (`grep -i "md-manager\|sand-\|space-\|geist\|mini\|pattaya"` returns empty).
- [ ] `plugins/flow/docs/workflow.md` exists, annotates `/simplify` (and `/batch`, `/debug`, `/loop`, `/claude-api`) as "(bundled with Claude Code)" wherever referenced, annotates `/critique-plan`+`/audit-plan`+`/audit-completion` as flow-internal, documents `flow.config.json` slots narratively, lists v1.0.0 scope and PR-2 backfill plan.
- [ ] `dev-docs/{plan,history,feedback,spec,workflow}.md` exist (all five files moved from `core-docs/`); `core-docs/` directory no longer exists.
- [ ] `plugins/flow/scripts/log_disagreement.py` writes to `~/.claude/plugins/data/flow/disagreements/` (grep for the new path; old `assumption-auditor` string absent).
- [ ] `.claude/rules/safety.md` lists the new `plugins/flow/*` paths; old root paths absent.
- [ ] `.claude/rules/general.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md` reference `dev-docs/` (not `core-docs/`); grep for `core-docs/` in `.claude/` returns empty.
- [ ] Root `README.md` describes the `flow` marketplace identity, includes install command, History section, and `pre-flow-plugin` tag reference.
- [ ] `CLAUDE.md` describes the new `plugins/flow/*` layout, `dev-docs/` convention, and the consumer-vs-plugin distinction (`template/core-docs/` vs `dev-docs/`).
- [ ] `grep -rn "llm-auditor\|assumption-auditor" .claude-plugin/ plugins/ README.md CLAUDE.md` returns only intentional history-tag references (in README "History" section and any commit-message archeology lines).
- [ ] `claude plugin validate .` exits clean.
- [ ] Local smoke test: `mkdir /tmp/flow-smoke && cd /tmp/flow-smoke && git init && claude` → `/plugin marketplace add <local-or-branch-ref>` → `/plugin install flow@flow` succeeds → `/help` lists `flow:ship`, `flow:audit-plan`, `flow:audit-completion`, `flow:critique-plan`, `flow:log-disagreement` (5 user-visible skills). If installing from the open branch fails because Claude Code can't read unmerged refs, document the failure and note "re-run smoke after merge" — don't block PR open on it.
- [ ] Manual cold-read pass complete: security (no command-injection in `` !`<cmd>` ``, no leaked paths, no secrets), simplification (no duplicated content between SKILL.md files, no dead text from md-manager source), project-agnostic (grep diff for `md-manager`, `pattaya`, `sand-`, `--space-`, `Geist`, `Mini`).

**Confidence verdicts (per load-bearing assumption):**

**Assumption:** Restructuring root content into `plugins/flow/*` via `git mv` preserves all behavior because skill files reference `${CLAUDE_PLUGIN_ROOT}/scripts/...` (dynamic) and `.claude-plugin/marketplace.json`'s plugin `source` slot is the only thing telling Claude Code where the plugin lives.
**Confidence:** HIGH
**Why:** Verified the three skill files (`critique-plan`, `audit-plan`, `audit-completion`, `log-disagreement`) all use `${CLAUDE_PLUGIN_ROOT}/scripts/...`. CLAUDE_PLUGIN_ROOT resolves dynamically to the installed plugin's path. The marketplace `source` field is the only static path reference and updates as part of this PR.
**If it flips:** A skill file has a hardcoded path that breaks after move. Smoke test (Step verify) catches it; fix the reference; the move stands. Single-file correction, not architectural.

**Assumption:** Renaming the marketplace from `llm-auditor` to `flow` and plugin from `assumption-auditor` to `flow` doesn't break any existing user installs in a way we have to handle gracefully. Pre-PR-1 installs will simply stop receiving updates until users re-run `/plugin marketplace add by-dev-tools/flow && /plugin install flow@flow`.
**Confidence:** HIGH
**Why:** Anthropic plugins are identified by `marketplace-name@plugin-name`; renaming both ends produces a new identity that the user must opt into. No silent breakage — the old key continues to point at a marketplace key that no longer exists, so the user sees an obvious "update failed" prompt. User is currently the sole consumer; coordinated migration is a one-line settings.json edit.
**If it flips:** Some Claude Code internal caches the old identity in a way that breaks the user's session on next launch. Mitigation: PR body documents the one-line settings.json edit + explicit `/plugin marketplace remove llm-auditor` if needed. The user already has a settings.json backup from PR 0 at `~/.claude/settings.json.bak.20260523-144832`.

**Assumption:** md-manager's `.claude/skills/ship/SKILL.md` (the port source for `/flow:ship`) ports per the locked PR-1 table at ~19% replacement rate (the consolidation doc's metric from the prior closed PR-1 attempt). Specifically: 3a stays active, 3b becomes a placeholder, security+a11y review invocations become placeholders, `typecheckCmd` becomes a loud-warning config slot, doc paths become config slots, default-branch becomes a fallback chain.
**Confidence:** MEDIUM
**Why:** The 19% metric came from a prior agent's port attempt against the SAME source file in a DIFFERENT host repo. The locked port table is stable. But: (a) md-manager's `/ship` source may have evolved since that estimate (I haven't read it yet — fetch + read happens during execution), and (b) edge cases in the port (e.g., new pipeline steps added to `/ship` in md-manager since the estimate) could push the replacement rate higher.
**If it flips:** If replacement exceeds ~30% (the prior re-plan trigger threshold), surface a mid-execution re-plan to the user rather than silently absorb scope. The mitigation pattern is exactly what the prior PR-1 attempt did with the `/simplify`-is-bundled discovery — proposal + approval, not silent expansion. Adds one round-trip; no architectural change.

**Assumption:** The `core-docs/` → `dev-docs/` rename doesn't break any rules/agents/skills under `.claude/` that read from `core-docs/` paths, because we update all references atomically in the same commit as the rename.
**Confidence:** MEDIUM
**Why:** The grep shows `.claude/rules/general.md`, `.claude/agents/*.md`, and `.claude/skills/*/SKILL.md` reference `core-docs/` paths. Atomic update is straightforward in principle, but path references can hide in non-obvious places (e.g., `paths:` frontmatter for rule auto-load, glob patterns in skills' `!` shell-substitution blocks). The risk is a missed reference that silently fails (a rule that no longer auto-loads, a skill whose context-injection cat-fails).
**If it flips:** A project-dev rule or agent stops working correctly in mid-PR. Discovery happens when the agent next tries to invoke that rule/agent during PR 1 execution itself, and the failure mode is visible (rule doesn't load, agent reports cat-error). Mitigation: pre-rename grep + post-rename verification grep + smoke-invoke each updated agent/skill at least once before push. Single-commit reversion is trivial if needed.

**Assumption:** `pre-flow-plugin` tag created against current HEAD (`8857ebd`) is sufficient as the recovery anchor — i.e., users (the user) can run `git checkout pre-flow-plugin` on the merged main branch and see the pre-restructure state.
**Confidence:** HIGH
**Why:** Standard git tag operation; `git push origin pre-flow-plugin` persists the tag remotely. The brief explicitly names this as the recovery mechanism.
**If it flips:** Tag push fails (auth / branch-protection issue). Trivial to retry; surface to user if it persists.

**Assumption:** Moving `.claude-plugin/plugin.json` from repo root to `plugins/flow/.claude-plugin/plugin.json` is the correct Anthropic-pattern shape — i.e., marketplace.json lives at repo root, plugin.json lives inside the plugin's own subdirectory.
**Confidence:** HIGH
**Why:** Verified against `code.claude.com/docs/en/plugin-marketplaces` in the prior consolidation session: marketplace.json at root + `plugins/<name>/.claude-plugin/plugin.json` inside is the explicit pattern. The current flat layout (both manifests at root) was acceptable when there was only ever going to be one plugin; the marketplace pattern formalizes the separation.
**If it flips:** `claude plugin validate .` rejects the new layout. Surface, fix path, re-validate. Single fix, no architectural impact.

**Risks / open questions:**
- **`log_disagreement.py` storage path orphan.** Renaming `~/.claude/plugins/data/assumption-auditor/disagreements/` → `~/.claude/plugins/data/flow/disagreements/` orphans any pre-existing disagreement records on the user's machine. Acceptable: it's local debug/dev data; the user has been the sole consumer; called out in README + PR body so the user can `mv` the old dir manually if they want continuity.
- **`/ship` port may surface unknown coupling.** If the md-manager source has evolved since the prior port-attempt's 19% estimate (e.g., new memory machinery references, new review skills baked in), the port could spill scope. Mitigation per the prior PR-1 pattern: surface re-plan rather than silently absorb. Re-plan trigger threshold is >30% replacement.
- **`/plugin marketplace add` from an unmerged branch.** The brief notes `/tmp/flow-smoke` may not be able to install from an open branch ref. If so, document and proceed; smoke can be re-run post-merge. Don't block PR open on this.
- **The `pre-flow-plugin` tag doesn't exist yet.** Verified empty via `git tag --list` and `gh api repos/by-dev-tools/flow/git/refs/tags` (404). The plan creates it as Step A. If for some reason tag creation fails (auth, branch-protection on tag namespaces), surface to user — the restructure is destructive enough that a recovery anchor is non-negotiable.
- **Marketplace `source` field shape.** The current marketplace.json declares `"source": "./"` because there's only one plugin and it lives at root. After restructure, `source` becomes `"plugins/flow"` (or `metadata.pluginRoot: "./plugins"` + `"source": "flow"` per the consolidation doc's docs-verified pattern). I'll use the `pluginRoot` form per Anthropic's example — cleaner if more plugins ever ship.
- **`spec.md` legacy content.** The current `core-docs/spec.md` describes the assumption-auditor product (audit categories, plugin scope, etc.). After rename to `dev-docs/spec.md`, this content describes flow's *audit-side* legacy product, but flow's broader workflow-plugin identity now exceeds what that spec covers. PR 1 preserves spec.md verbatim under the rename (do not rewrite scope in PR 1 — that's a separate dev-docs hygiene PR if needed). Flag in handoff notes that dev-docs/spec.md will need broadening in a follow-up.

**Files touched (anticipated):**

**Moves (`git mv` — history preserved):**
- `agents/auditor.md` → `plugins/flow/agents/auditor.md`
- `agents/plan-critic.md` → `plugins/flow/agents/plan-critic.md`
- `skills/audit-plan/SKILL.md` → `plugins/flow/skills/audit-plan/SKILL.md`
- `skills/audit-completion/SKILL.md` → `plugins/flow/skills/audit-completion/SKILL.md`
- `skills/critique-plan/SKILL.md` → `plugins/flow/skills/critique-plan/SKILL.md`
- `skills/log-disagreement/SKILL.md` → `plugins/flow/skills/log-disagreement/SKILL.md`
- `scripts/extract_session.py` → `plugins/flow/scripts/extract_session.py`
- `scripts/bounding_logic.py` → `plugins/flow/scripts/bounding_logic.py`
- `scripts/log_disagreement.py` → `plugins/flow/scripts/log_disagreement.py`
- `evals/run_evals.py` → `plugins/flow/evals/run_evals.py`
- `evals/ground_truth.yaml` → `plugins/flow/evals/ground_truth.yaml`
- `evals/fixtures/` → `plugins/flow/evals/fixtures/`
- `DISAGREE.md` → `plugins/flow/DISAGREE.md`
- `.claude-plugin/plugin.json` → `plugins/flow/.claude-plugin/plugin.json`
- `core-docs/plan.md` → `dev-docs/plan.md`
- `core-docs/history.md` → `dev-docs/history.md`
- `core-docs/feedback.md` → `dev-docs/feedback.md`
- `core-docs/spec.md` → `dev-docs/spec.md`
- `core-docs/workflow.md` → `dev-docs/workflow.md`

**Modified (post-move):**
- `.claude-plugin/marketplace.json` (rename names, URLs, source, pluginRoot, version, description)
- `plugins/flow/.claude-plugin/plugin.json` (rename, version bump, URLs, description)
- `plugins/flow/scripts/log_disagreement.py` (storage path rename)
- `README.md` (rewrite for marketplace identity)
- `CLAUDE.md` (update layout references)
- `.claude/rules/safety.md` (update safety-critical path list)
- `.claude/rules/general.md` (`core-docs/` → `dev-docs/`)
- `.claude/agents/{planner,domain,testing,docs}.md` (`core-docs/` → `dev-docs/`)
- `.claude/skills/{ship,preship}/SKILL.md` (`core-docs/` → `dev-docs/`)

**New:**
- `plugins/flow/skills/ship/SKILL.md` (port from md-manager)
- `plugins/flow/docs/workflow.md` (port from md-manager)

**Tag:**
- `pre-flow-plugin` at `8857ebd` (pushed to origin)

**Execution sequence** (each step → its own commit unless trivially small):

1. **Step A — Recovery tag.** `git tag pre-flow-plugin 8857ebd && git push origin pre-flow-plugin`. Verify via `git ls-remote --tags origin`.
2. **Step B — Restructure (move).** `git mv` all 19 file/dir paths above into `plugins/flow/*` and `dev-docs/*`. Move `.claude-plugin/plugin.json` into `plugins/flow/.claude-plugin/plugin.json`. Single commit: "Restructure: hoist plugin artifacts into plugins/flow/; rename core-docs/ → dev-docs/".
3. **Step C — Manifest rename.** Update `.claude-plugin/marketplace.json` and `plugins/flow/.claude-plugin/plugin.json` for `flow` identity + v1.0.0 + by-dev-tools URLs + descriptions. Validate with `jq .` + `claude plugin validate .`. Commit: "Rename marketplace + plugin to flow; bump to 1.0.0".
4. **Step D — log_disagreement storage path.** Edit `plugins/flow/scripts/log_disagreement.py` for the `assumption-auditor` → `flow` storage-dir rename. Commit: "Rename disagreement storage path: assumption-auditor → flow".
5. **Step E — Reference updates under `.claude/`.** Grep + edit all `.claude/rules/`, `.claude/agents/`, `.claude/skills/` references for `core-docs/` → `dev-docs/` and old root paths → `plugins/flow/*`. Commit: "Update project-dev infra path references for restructure".
6. **Step F — Port `/flow:ship`.** Fetch md-manager's `.claude/skills/ship/SKILL.md` via `gh api`. Read it. If replacement rate looks >30%, surface re-plan before writing. Otherwise port per the locked PR-1 table → `plugins/flow/skills/ship/SKILL.md`. Commit: "Add /flow:ship skill (ported from md-manager; PR 2 backfills placeholders)".
7. **Step G — Port `workflow.md`.** Port `/tmp/md-workflow.md` → `plugins/flow/docs/workflow.md` per the de-projection rules above. Commit: "Add canonical workflow.md (de-projected; v1.0.0 scope notes)".
8. **Step H — Rewrite README + CLAUDE.md.** Marketplace identity in README; new layout in CLAUDE.md. Commit: "Rewrite README + CLAUDE.md for flow marketplace identity".
9. **Step I — Manual cold-read pass.** Run greps for md-manager-specific tokens; check for command-injection in `` !`<cmd>` ``; verify no secrets / hardcoded user paths. Apply fixes inline. Commit only if fixes: "Manual review pass: <findings>".
10. **Step J — Verification.** `claude plugin validate .` clean; `jq .` parses both manifests; smoke test in `/tmp/flow-smoke` per the spec-walk checklist. Capture any smoke-test friction in `dev-docs/feedback.md` to surface in PR 2.
11. **Step K — Push + open PR.** `git push -u origin claude/trusting-jackson-0de7f4`; `gh pr create --base main --title "PR 1: Restructure into plugins/flow/; rename to flow@1.0.0; add /flow:ship + workflow.md" --body "..."`. Output PR URL. **Do not merge.**

---

## Recently Completed

- **v0.3.0 — auto-invoked disagreement loop** (PR #3, 2026-04-XX) — see `dev-docs/history.md` (post-rename) for full entry.

## Backlog

(Items below predate the flow extraction; preserved for continuity. Most fold into PR 2 or post-extraction roadmap.)

- Verification skill (sibling plugin) — see prior plan content at `pre-flow-plugin` tag for full context. Reassess after extraction settles.
- Wire `evals/run_evals.py` to live auditor subagent invocation (remove `.expected.txt` stub) — flow-internal eval improvement, post-extraction.
- Capture fixtures for `trio_navigation_stack_cycle_3`, `portfolio_blank_screen`, `trio_morphing_recall`.
- Structured output schema for auditor (replace substring matching in eval checks).
- Expand artifact regex beyond the hardcoded 28-extension list in `plugins/flow/scripts/extract_session.py` (post-restructure path).
- Raise or remove the 50-call tool-history cap in `plugins/flow/scripts/extract_session.py`.
- Generalize hardcoded SwiftUI proxy handling to other frameworks.
- Broaden `dev-docs/spec.md` beyond the audit-only scope to cover flow's full workflow-plugin identity (follow-up hygiene PR after extraction).
