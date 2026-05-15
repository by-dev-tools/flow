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

### Plan-critic sibling reviewer + marketplace metadata for v0.2.0
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
