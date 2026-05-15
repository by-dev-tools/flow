# History

Detailed record of shipped work. Reverse chronological (newest first). This is not a changelog -- it captures the **why**, **tradeoffs**, and **decisions** behind each change so future sessions have full context on how the project evolved.

---

## How to Write an Entry

```
### [Short title of what was shipped]
**Date:** YYYY-MM-DD
**Branch:** branch-name
**Commit:** [SHA or range]

**What was done:**
[Concrete deliverables -- what changed in user-facing terms.]

**Why:**
[The problem this solved or the goal it served.]

**Design decisions:**
- [UX or product choice + reasoning]

**Technical decisions:**
- [Implementation choice + reasoning]

**Tradeoffs discussed:**
- [Option A vs Option B -- why this one won]

**Lessons learned:**
- [What didn't work, what did, what to do differently]
```

Use the `SAFETY` marker on any entry that modifies error handling, persistence, data loss prevention, or fallback behavior.

---

## Entries

<!-- Add new entries below this line, newest first. -->

### Auto-invoked disagreement loop for v0.3.0
**Date:** 2026-05-15
**Branch:** [pending]
**Commit:** [pending]

**What was done:**
Closed the feedback loop on the auditor and plan-critic so users can register disagreement with a specific finding in plain language, without invoking a slash command. The plugin now ships an auto-invoked `log-disagreement` skill that the model triggers when it detects pushback on a recent finding, captures the session window and dispute metadata to user-scope storage, and confirms the capture in a single line.

Concrete artifacts:
- `skills/log-disagreement/SKILL.md` — model-invokable skill (`disable-model-invocation` omitted; default behavior allows the model to invoke). Description lists explicit invocation triggers (plain-language disagreement after an audit output) and anti-triggers (general conversation, acceptance, unrelated pushback). Body instructs the model to extract reviewer/category/severity/claim/reason and dispatch the capture script.
- `scripts/log_disagreement.py` — captures the session window from the audit output forward (last ~12 turns by default) into a `.jsonl` plus a `.meta.json` with the structured dispute fields. Stored under `~/.claude/plugins/data/assumption-auditor/disagreements/` so disputes accumulate across projects and survive workspace cleanup.
- `agents/auditor.md` and `agents/plan-critic.md` — added an "Output footer (always)" section requiring every output to end with the disagreement invitation. The footer is part of the schema, not commentary, so the existing "do not add commentary before or after" discipline remains intact.
- `evals/fixtures/*.expected.txt` — footer appended to all five existing fixtures so they stay aligned with the new schema. The harness is still stubbed; once live invocation lands, expected outputs and live outputs will match exactly.
- README updated with the auto-invocation flow and a new entry in the slash-command table.
- `.claude-plugin/{plugin,marketplace}.json` bumped to 0.3.0 with descriptions reflecting the new feedback channel.

**Why:**
The v0.2.0 feedback loop was open: when a reviewer's output was wrong, users had to manually edit `DISAGREE.md` to register the disagreement. Most users would not bother. Maintainer-side prompt tuning depended on disagreements being captured, which depended on users doing free work — a brittle loop that empirically yielded zero entries in `DISAGREE.md` across the v0.1.0–v0.2.0 cycle. Without captured disputes the next prompt tune is data-blind; with them, every false positive becomes a regression test.

The forcing function: as the plan-critic moves toward being a real approval gate (md-manager integration just shipped), the cost of a bad critic finding rises. Users will tolerate occasional false positives only if they have a near-zero-cost way to flag them. Manual `DISAGREE.md` editing fails that bar; "just say so in chat" passes it.

**Design decisions:**
- **Model-invokable skill instead of a hook.** Two options for auto-invocation: a `UserPromptSubmit` hook (deterministic but keyword-based) or a model-invokable skill (nuanced but probabilistic). Chose the skill because plain-language disagreement is too varied for keyword matching to catch well — "actually the scope is fine here" is disagreement; a keyword hook would miss it. The trade-off is silent-miss risk when the model fails to recognize disagreement. Mitigated by the explicit invitation footer (gives the user a near-explicit trigger) and by a documented v0.3.1 follow-up to add a hook as a deterministic safety net if smoke-testing shows the miss rate is non-trivial.
- **User-scope storage, not project-scope.** Disagreements are plugin-improvement data, not project data. A project-scope log would scatter the feedback across repos and make maintainer-side analysis hard. User-scope under `~/.claude/plugins/data/` mirrors how forge stores its data and survives project deletion.
- **Two paired files per disagreement.** `.jsonl` for the session window (fixture-skeleton), `.meta.json` for the structured fields (queryable). Splitting them means the maintainer can `cat *.meta.json | jq` to triage disputes without parsing session JSONL, while still having the session content available for promoting a disagreement to an eval fixture.
- **Footer in the output schema, not in the skill output.** The footer needs to be inside the subagent's prescribed output so the existing "do not add commentary" rules don't conflict with it. Wrote it as a schema section, not a special case, so future schema additions follow the same pattern.
- **No automatic promotion to eval fixture.** Disagreements land as candidates; promoting them to `evals/fixtures/` is still a manual maintainer step. Tempting to auto-promote but risky — a single misclassified disagreement becomes a permanent regression test pinning the wrong behavior. Manual review remains the gate.

**Technical decisions:**
- **`datetime.datetime.now(datetime.timezone.utc)` instead of `utcnow()`.** Python 3.7+ stdlib only is the project constraint. `utcnow()` is deprecated in 3.12+; `now(timezone.utc)` works in 3.2+ and isn't deprecated. Future-proof at zero cost.
- **`SESSION_CAPTURE_WINDOW = 12` and `start = max(0, audit_idx - WINDOW//2)`.** Captures from a few turns before the audit forward, so the fixture includes the user request, the plan/completion, the audit output, and the user's pushback. Empirically sized; tuneable in a follow-up if it captures too little or too much.
- **Walking records back-to-front for audit detection.** `find_recent_audit_record_idx` scans for assistant turns containing `AUDIT SUMMARY` / `CRITIQUE SUMMARY` / `ISSUE ·` / `No issues flagged` / `APPROVED`. Marker-based detection is brittle to future schema changes but cheap; documented as a known coupling.
- **Slugify the category for the filename.** Prevents collision when multiple disputes land in the same second (rare but possible) and keeps filenames filesystem-safe across platforms.
- **The skill calls the script via `Bash` only.** No file-edit tools needed in the skill; the model just packages the dispute fields and runs the script. Smaller blast radius.

**Tradeoffs discussed:**
- **Auto-invoke vs explicit `/disagree` slash command:** explicit is more reliable but adds friction; auto-invoke is frictionless but risks silent miss. Chose auto-invoke with the explicit-invitation footer as a hybrid — the model has full context to detect disagreement, the user has an obvious channel to push back. The silent-miss tradeoff is acknowledged and has a documented mitigation path.
- **Footer wording:** considered "Disagree? Just say so." (terse), "If a finding is wrong, just say so. Your pushback will be logged for prompt tuning." (chosen — explicit about both the channel and what happens to the input), and a longer explanation of the loop (rejected as commentary).
- **CLAUDE.md fragment for reliability:** original plan included a CLAUDE.md instruction telling the model to invoke `/log-disagreement` on detected disagreement. Plugins cannot inject CLAUDE.md fragments into host projects, so dropped. The skill description and footer carry the same instruction-load now.
- **Bumping plan.md Current Focus to reference v0.3.0:** could have left it pointing at the v0.2.0 next-step (live eval invocation). Updated so the document reflects the current state; live-eval-invocation moves to the "next load-bearing step" framing inside the v0.3.0 entry.

**Safety:**
Touches `agents/auditor.md` and `agents/plan-critic.md` — both safety-critical per `.claude/rules/safety.md`. The change is additive (a new schema section requiring a footer) and does not modify, weaken, or remove any existing discipline: the "evidence or silence" rule, the two-citation rule, the forbidden phrases, the permission-to-find-nothing clause are all preserved. Existing fixtures' expected outputs were updated to include the new footer so the regression set stays aligned. The footer text is invariant ("If a finding is wrong, just say so. Your pushback will be logged for prompt tuning.") — no variability that could erode reviewer discipline. Marked here per the safety rule's "Flag the change" requirement, though strictly this isn't an error-handling / persistence / fallback change.

**Lessons learned:**
- The "model-invokable skill description" doubles as documentation of the auto-invocation contract. Wrote it carefully because it's the only line of defense against silent miss — the more concrete and exemplified the description, the higher the recognition rate. Treating it like a regular skill description (one-line summary) would have been worse than the alternative.
- The footer being part of the *schema* matters. Putting it in commentary territory would create a "the prompt says no commentary, but it also requires this commentary" contradiction. Naming it as a schema element resolves the conflict cleanly. Worth remembering for any future schema additions.
- Storage location reveals product intent. User-scope under `~/.claude/plugins/data/` signals "this is plugin-improvement data, not project data." Project-scope would have signaled "this is a per-project audit log" — a different (and worse for this use case) product.


**Date:** 2026-05-14
**Branch:** project-status-overview
**Commit:** 8ce9fb3

**What was done:**
Added a second skeptical reviewer alongside the existing auditor: the **plan-critic**, which checks proposed plans for *reasoning* gaps (scope drift, spec violation, internal incoherence) rather than *evidence* gaps. Shipped as v0.2.0.

Concrete artifacts:
- `agents/plan-critic.md` — prompt with three categories, a two-citation discipline (every finding cites both a source of truth and the conflicting plan element), and three severity tiers (BLOCKER / REDIRECT / FOLLOW-UP). Explicit `APPROVED` signal for clean plans.
- `skills/critique-plan/SKILL.md` — user-invocable entry point. `disable-model-invocation: true`, `context: fork`, `agent: plan-critic`. Mirrors the existing `audit-plan` skill pattern. Invokes the preprocessor with `--reference-glob "core-docs/*.md"`.
- `scripts/extract_session.py` extended with `--reference-paths` and `--reference-glob` (opt-in). Reads matching docs from CWD; skips `history.md` / `plan.md` / `roadmap.md`; caps each doc at 12000 chars; renders a `## Reference documents` section above the existing context. Existing audit-plan / audit-completion flows produce byte-identical output when the new flags aren't passed.
- `evals/fixtures/scope_drift_form_fix.{jsonl,expected.txt}` — exercises scope drift.
- `evals/fixtures/spec_violation_bundled_ui.{jsonl,expected.txt}` — exercises spec violation; reference rule embedded via in-session Read of `core-docs/feedback.md`.
- `evals/fixtures/internal_incoherence_jwt_migration.{jsonl,expected.txt}` — exercises internal incoherence; two contradictory plan steps (keep + remove the same middleware file).
- `evals/ground_truth.yaml` — new entries with a `reviewer: plan-critic` field for future harness dispatch.
- Marketplace + plugin metadata enriched to match the `forge` pattern (owner, version, keywords, homepage, repository, category).

**Why:**
The existing auditor is rigorous but narrow — it can only flag claims that lack session evidence. It misses a different failure class: plans whose *reasoning* is misaligned with intent. Plans that silently expand scope, contradict a documented rule, or contain internal contradictions don't lack evidence — they lack alignment. The plan-critic is the sibling lens for that class.

The md-manager workflow's plan-approval gate (step 3 of its workflow.md) was the proximate forcing function. That gate is currently a human-only check; the long-term goal is to stage trust so an agent can review plans at the gate. The plan-critic is the first credible candidate to do so.

**Design decisions:**
- **Sibling subagent, not a fifth auditor category.** The auditor's discipline is "evidence or silence" — adding reasoning categories would dilute it. Two prompts, shared plumbing, no cross-references is the right separation.
- **Two-citation rule as the falsifier-equivalent.** The auditor demands a tool-call citation; reasoning critique can't. The substitute discipline: every finding must produce one quote from a source of truth, one quote from the plan element, plus one sentence of glue. If the critic can't produce both quotes, no flag. Same epistemic stance as "evidence or silence."
- **Severity tiers in the output.** Auditor output is binary (issue / no-issue). For an approval-gate use case, a calling agent needs to distinguish "must fix before approval" from "note and proceed." BLOCKER / REDIRECT / FOLLOW-UP imported from the md-manager `staff-review` skill pattern.
- **Deterministic doc loading via preprocessor.** Reference docs are inputs; loading them belongs in the preprocessor, not in the subagent's tool use. This keeps the critic's context predictable and removes its dependency on what Claude happened to Read during the session.
- **Default skip list.** `history.md` (decision log), `plan.md` (work tracker), `roadmap.md` (future work) are *not* sources of truth for new plans. Loading them would inject noise and stale state. Excluded by default; user can override with explicit `--reference-paths`.

**Technical decisions:**
- **Glob-with-skip-list, not explicit-paths-only.** Glob is more ergonomic for projects following the `core-docs/` convention. Explicit `--reference-paths` available as override for non-conventional layouts.
- **12000-char cap per doc.** Sized to fit typical `spec.md` / `feedback.md` / `design-language.md` / `workflow.md` without truncation. Adds a `(truncated; original N chars)` marker when it does fire. Cap is per-doc, not total, since the critic reads them as separate quotable units.
- **`reviewer: plan-critic` field in ground_truth.yaml.** Forward-looking — the eval harness doesn't dispatch on it yet (still reads `.expected.txt` stubs for both reviewers), but adding the field now means the harness rewire only needs to read what's already there.
- **README registers both reviewers explicitly.** The "Slash commands" table at the top is the install-and-go contract. Sub-tables for each reviewer's categories. Output formats documented separately.

**Tradeoffs discussed:**
- **Plugin vs. in-repo for md-manager:** could have built the critic directly in md-manager. Decided against — the categories are generic, the infrastructure already exists in this plugin, and md-manager isn't the only project that will benefit. Cost of the plugin dependency is one `/plugin install` per consumer.
- **Bundle into forge marketplace vs. independent:** could have added the critic to the existing forge marketplace for a unified surface. Decided against — different products (forge = infrastructure architect, auditor = session reviewer), different release cadence, easier to spin off if maintenance shifts. Two marketplaces costs users one extra `/plugin marketplace add` command. Trivial.
- **Ship plan-critic in v0.2.0 vs. hold experimental:** plan-critic hasn't been battle-tested on real sessions. Shipping anyway because the md-manager workflow change depends on `/critique-plan` existing. README is honest that the third category (internal incoherence) lacks a fixture and that the eval harness is still stubbed. Better to ship with honest limitations than block the consumer workflow.
- **History entry written before commit:** the docs discipline rule requires history.md updated before commit. Entry written now with `Commit: [pending]` placeholder; replace with SHA on the actual commit.

**Lessons learned:**
- The "two-citation rule" framing took several passes to land. Initial drafts asked for "specific quotes" or "concrete evidence" — too vague. Naming the structure (one quote from truth, one from the plan, one sentence of glue) made the discipline enforceable. Worth doing the same exercise for any future reviewer category.
- The preprocessor-vs-subagent question for doc loading kept coming back. Multiple options seemed plausible (extend preprocessor, sibling preprocessor, subagent Read tool, pre-flight skill, host-project rule). The right factoring was clear once the question was "which component is responsible for deterministic input?" — that's the preprocessor's job, always.
- README discipline matters at the marketplace boundary. The bare marketplace.json (the v0.1.0 version) would have shipped fine for self-install but looked unfinished in any discovery surface. Filling in keywords / homepage / category is 10 minutes of work; doing it before publish saves a "looks abandoned" first impression.


**Date:** 2026-04-20
**Branch:** codebase-overview
**Commits:** e30b75b, 4d3522b, + in-progress fixup

**What was done:**
Added `CLAUDE.md`, `core-docs/`, and `.claude/` scaffolding for developing the plugin. Kept the new project-dev files strictly separate from the plugin's own published artifacts (root `agents/`, `skills/`, `scripts/`, `evals/`, `.claude-plugin/`, `README.md`, `DISAGREE.md`). Added a `.gitignore` for `.claude/settings.local.json`, `.claude/forge/`, and `.DS_Store`.

**Why:**
Before this change, the repo had no project-dev infrastructure -- no agent specs, no rules, no living docs. Sessions developing the plugin had to rediscover context every time. The template provides a scoped, predictable place for that context.

**Design decisions:**
- Explicit plugin-vs-dev boundary documented at the top of CLAUDE.md. The dual-name collision (`agents/` at root vs. `.claude/agents/`) is structural -- Claude Code's plugin convention requires plugin artifacts at root, and Claude Code's project convention requires project-dev infra under `.claude/`. Resolved via documentation, not reorganization.
- Renamed `.claude/skills/audit/` to `.claude/skills/preship/` to avoid slash-command collision with the plugin's own `/audit-plan` and `/audit-completion`. The pre-ship skill's frontmatter `name:` was updated to match (caught in review -- would otherwise have registered as `/audit`).
- Deleted template pieces inapplicable to a headless plugin: `core-docs/design-language.md`, `.claude/agents/ui.md`, `.claude/rules/ui.md`, `.claude/rules/dev-server.md`, `.claude/skills/link/`, `.claude/skills/dev-panel/`, `.claude/skills/setup/`.
- Scoped `.claude/rules/safety.md` to plugin-critical files: `agents/auditor.md`, `scripts/*.py`, plugin manifests, eval harness. These are the files whose silent breakage would be most expensive.

**Technical decisions:**
- `.claude/settings.local.json` gitignored per Claude Code convention (per-user permissions should not be shared).
- Empty `.claude/forge/` directory left in tree (git doesn't track empty dirs) but gitignored to prevent Forge's local cache from being committed later.
- `core-docs/plan.md` Current Focus populated with the real v0.1.0 state (eval harness stub + SKIP'd fixtures) rather than left as a template placeholder.

**Tradeoffs discussed:**
- Keep vs. rename `.claude/skills/audit/`: renaming adds a small cognitive cost (users typing `/audit` won't find it) but eliminates a real collision risk during plugin development. Renaming won.
- Populate vs. leave template placeholders in `plan.md`/`history.md`/`feedback.md`: populated plan.md because the current focus is knowable and useful; left history.md and feedback.md format-only because the first real entries should come from real work, not backfill.
- Merge template README content into the existing plugin README: skipped. Template README is generic philosophy; plugin README is concrete install/use docs. Nothing to merge.

**Lessons learned:**
- Directory renames don't automatically update frontmatter `name:` fields. Always grep for the old name after a skill rename. The preship skill's frontmatter was missed in the first pass and caught in self-review -- the exact kind of "declared done, didn't actually verify" error the plugin itself is designed to catch.
- Full-repo grep for references to deleted files (`design-language`, `UI Agent`, etc.) after cleanup is load-bearing. Four agent/workflow files had stale references the deletion step missed.
