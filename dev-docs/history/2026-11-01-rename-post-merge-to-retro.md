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
- **A self-authored redirect stub was considered and explicitly rejected, not overlooked.**
  `/simplify`'s altitude lens correctly pointed out that "no host-provided alias" doesn't preclude
  a one-line `plugins/flow/skills/post-merge/SKILL.md` stub that just says "renamed, run
  `/flow:retro`" — that's real and the dispatch anticipated it directly: "if aliases aren't a real
  mechanism, say so and ship the straight rename **instead of inventing one**." Taken as a
  deliberate instruction, not a gap in the check. The real cost this absorbs: a saved shortcut or
  a script invoking `/flow:post-merge` non-interactively breaks with no redirect — flagged
  explicitly in the changelog's new "Breaking changes" line (added after the same lens caught its
  absence) rather than silently accepted.
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
  "✅ SHIPPED (v1.21.0...)" block (which also retains a deferred v1b design record) was initially
  left as a historical/design retention wholesale, on the reasoning that parsing it clause-by-clause
  for shipped-v1 (leave) versus still-open-v1b (fix) prose was disproportionate to a small rename
  task. `/flow:staff-review`'s staff-engineer lens correctly caught one exception inside that same
  block: its "v1b staff-review follow-ups... **Surfaces when:**" line is not narrative at all — it's
  an actionable trigger naming a path, and that path (`skills/post-merge/...`) no longer exists.
  Fixed (two path strings); everything else in the block stayed as retained prose, since the "is this
  an actionable trigger naming a current path, or is it narration" test — not "is it inside a SHIPPED
  header" — is what actually decides it, and the rest of that block genuinely is narration.
- **`postMergeWaitSeconds`'s key stays unrenamed, for a sturdier reason than "it's config, not the
  command."** That framing is true but not the load-bearing one. The real reason: `flow.config.json`
  is a consumer-owned artifact, and any project that already set this key would have it silently
  stop being read if the key were renamed with no back-compat alias and no `⚠️` warning — exactly
  the "never silently no-op on a missing slot" failure CLAUDE.md names directly. Leaving the slot
  name alone and only updating its description text is correct for that reason, not merely because
  config and command names are different categories.

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
- `/simplify`'s altitude lens caught something the other three lenses (and the author) missed on a
  diff that looked "too mechanical to need a quality pass": `CHANGELOG.md` states its own format
  contract — every entry needs a "Breaking changes:" line — and the new `changelog/v1.66.0.md`
  skipped it on the reasoning that a pure find-and-replace rename "obviously" isn't the kind of
  change that needs one. It is exactly that kind of change: the one place consumers are told to
  check before upgrading is precisely where a hard rename with no alias should have been flagged.
  A diff's apparent simplicity doesn't exempt it from the project's own documented contracts.
