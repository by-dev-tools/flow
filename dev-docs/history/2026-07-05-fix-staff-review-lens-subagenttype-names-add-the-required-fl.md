### Fix staff-review lens `subagent_type` names — add the required `flow:` prefix
**Date:** 2026-07-05
**Branch:** claude/peaceful-roentgen-58993a
**Commit:** [pending]

**What was done:**
Corrected the Step 3 lens table in `plugins/flow/skills/staff-review/SKILL.md`. The four `subagent_type` values now carry the plugin namespace: `flow:lens-staff-engineer`, `flow:lens-ux-designer`, `flow:lens-design-engineer`, `flow:lens-push-further` (were unprefixed). Also tightened the Step 3 prose (line 56) to state explicitly that `subagent_type` must be the plugin-namespaced name and that the bare frontmatter `name:` is rejected.

**Why:**
The Agent tool registers plugin agents under their `flow:`-prefixed names. Following the doc verbatim (`lens-staff-engineer`) made all four lens spawns fail with `Agent type 'lens-staff-engineer' not found. Available agents: … flow:lens-staff-engineer …`, forcing a retry on every `/flow:staff-review` run.

**Technical decisions:**
- Only the `subagent_type` column changed. The "Agent file" column still points at the on-disk `${CLAUDE_PLUGIN_ROOT}/agents/lens-*.md` paths, which are correctly unprefixed — the prefix is a registry-namespace artifact, not a filename. Verified the four names against each agent's frontmatter `name:` and against the live Agent registry listing.

**Tradeoffs discussed:**
- Could have left the prose at line 56 untouched (it didn't name specific agents). Rewrote it anyway to pin down *why* the prefix is required, so a future editor doesn't re-introduce the unprefixed form from the frontmatter `name:` — an instance of FB-0010's fan-out-contradiction class (a name referenced in table + prose where only one copy was correct).

**Lessons learned:**
- Plugin-agent `subagent_type` is the namespaced name (`flow:<name>`), not the frontmatter `name:`. Any doc or code that spawns a plugin agent must use the prefixed form.
