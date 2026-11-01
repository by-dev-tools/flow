# Rename `/flow:post-merge` to `/flow:retro`

**Date:** 2026-11-01
**Branch:** `conductor/rename-post-merge-to-retro`
**Version:** v1.66.0
**Feedback:** FB-0141
**Scope:** `plugins/flow/skills/post-merge/` → `plugins/flow/skills/retro/` and every live
reference to it.

## What was done

Renamed the skill directory and its frontmatter `name` from `post-merge` to `retro`, then fixed
every live reference across the plugin: `workflow-help/SKILL.md`'s catalog table,
`docs/workflow.md` (10 occurrences), `/flow:land`'s "called by" text and its
`post-merge/lib/merge-status.py` path reference, `doctor/SKILL.md`'s skill-composition-lint
example, `handoff/SKILL.md`'s archive-check path, the `postMergeWaitSeconds` schema slot's
description text (slot name unchanged — it's config, not the command), `README.md`'s skills
table, the canonical `research/2026-08-23-flow-cloud-workflow-plan.md`, and three eval harnesses
(`run_land_evals.py`, `run_merge_status_evals.py`, `run_skill_composition_evals.py`) whose live
assertions check the real composition contract against flow's own skills directory.

Also fixed several not-yet-picked-up `dev-docs/roadmap.md` § Next/§ Later items that named the
skill by path or name — those are forward-looking triggers for future work and would have
silently misdirected a future session to a directory that no longer exists.

Filed `dev-docs/roadmap.md` § Next entry for an unrelated gap relayed from `byamron/portfolio`
(a doc-currency version-gate fallback problem) — not built, per the dispatch's own instruction
that it's a separate, judgment-heavy design question.

## Why

Ben's own words, relayed from a different repo: he reaches for this skill as "the workspace
retro," and "post-merge" didn't come to mind when he went looking for it by name — even though
the name accurately described *when* the skill runs. A skill's shipped name is a user-facing API;
"technically accurate" and "the word the user reaches for" are different bars, and this one
missed the second.

## Design decisions

- **Confirmed no alias mechanism before deciding to do a straight rename.** The dispatch
  explicitly asked to check this rather than assume either way. Fetched Claude Code's own skills
  documentation: "Built-in aliases exist only for bundled skills and commands, such as `/review`
  for `/code-review`. You can't define your own." The "directory name also invokes the skill"
  behavior is documented only for personal/project skills, not plugin skills, so even that
  indirect route doesn't apply here. Straight rename, no deprecated-alias period.
- **Historical records left untouched.** `changelog/`, `dev-docs/history/`, other
  `dev-docs/feedback/` entries, and the "Shipped"/"Prior" narrative inside `dev-docs/plan.md` and
  `dev-docs/roadmap.md` § Now all describe what was true at the time those PRs shipped, under the
  name the skill had then. This is the same principle applied earlier this week when a stale
  version headline in `roadmap.md` § Now was corrected going-forward without rewriting the
  historical entries beneath it — rewriting past narrative to match a later rename would
  misrepresent history, not fix a bug.
- **Open roadmap items got fixed, historical narrative did not.** The dividing line wasn't
  "is this in `dev-docs/`" — it was "does this describe something that already happened (leave)
  or something that might still happen and needs the current path to find it (fix)." Several
  § Next/§ Later items were the latter and got the correct `retro/` path; the one explicitly
  "✅ SHIPPED (v1.21.0...)" block (which also retains a deferred v1b design record) was left as a
  historical/design retention rather than parsed clause-by-clause for which sentences describe the
  shipped v1 (leave) versus the still-open v1b spec (arguably fix) — the effort to split that
  precisely was disproportionate to a small rename task, and is named here rather than silently
  skipped.

## Tradeoffs discussed

- **Fixture skill names inside `run_skill_composition_evals.py`'s synthetic Layer-1 tests** (built
  in a tempdir to test the generic lint mechanism, using "post-merge" as a convenient example
  caller name) were deliberately **not** renamed — they're arbitrary test fixture identifiers
  unrelated to the real skill, and renaming them would have been pure churn with no functional or
  clarity gain. Layer 3's **live** assertions (which read flow's own actual skills directory) were
  renamed, since those are genuinely checking the real, renamed skill.

## Lessons learned

- A rename task's real risk isn't the rename itself — it's the fan-out. The mechanical grep found
  ~50 files; the judgment call was almost entirely about which of those describe *current* reality
  (fix) versus *past* reality (leave), and that distinction doesn't follow any single directory
  boundary (`dev-docs/roadmap.md` needed both kinds of edit within the same file).
