# E1 raw evidence — `InstructionsLoaded` hook logs

**Status:** raw experimental evidence, archived 2026-09-10. **Captured 2026-09-03.** Not maintained. Supports `../2026-09-agents-md-vs-skills.md` §5.1 (experiment E1).
**Deletion criterion (FB-0088):** delete this directory once **S0** lands and rule loading is verified by a **mechanical check** (an upgraded `/flow:doctor` Check 3.2 that asserts *activation*, not registration) rather than by these logs. Until that check exists, these files are the only reproducible evidence of the defect.

## What these are

Verbatim stdout of the Claude Code `InstructionsLoaded` hook, one JSON object per instruction-load event, captured during experiment E1. Three fresh authenticated sessions were started in the flow workspace on 2026-09-03 against **flow v1.36.0** (verified live — the probe listed 21 `flow:*` skills), each with the hook registered via a gitignored `.claude/settings.local.json`. Copied here byte-for-byte from `/tmp/e1lab/` (sha256 verified on copy); no field was reformatted, redacted, or reordered.

| File | Probe | What it read |
|---|---|---|
| `probe-1-plan-and-history.jsonl` | E1 probe 1 | `dev-docs/plan.md`, `dev-docs/history.md`, `plugins/flow/scripts/log_disagreement.py` |
| `probe-2-plugin-live-control.jsonl` | E1 probe 2 | `dev-docs/plan.md` (plus a self-report confirming the plugin was live) |
| `probe-3-project-scoped-skill.jsonl` | E1 probe 3 | `dev-docs/roadmap.md` (isolating project-scoped vs plugin-scoped skills) |

## Why these were kept — the non-obvious field is `trigger_file_path`

Each `path_glob_match` event records **which file read caused the load**. That turns a general negative into a paired observation on a single event:

> In probe 1, `trigger_file_path: .../dev-docs/plan.md` fired `.claude/rules/documentation.md` (a path-scoped **rule**, `globs: ["dev-docs"]`) — and did **not** fire `flow:plan-discipline` or `flow:documentation`, the two **skills** whose `paths:` frontmatter globs `**/plan.md`.

Same file, same read, same session: the rule mechanism fires, the skill mechanism does not. Probe 3 repeats it with `dev-docs/roadmap.md` and adds the scope control — a throwaway *project-scoped* skill with `paths:` also failed to fire, so the defect is not specific to plugin scope.

**This is what S0 needs.** S0 (`roadmap.md` § Now — restore rule loading) offers three options: (a) report upstream, (b) ship the four as `.claude/rules/*.md`, (c) accept model-invocation. Choosing between them turns on exactly this evidence — *which loading mechanism actually fires* — and re-running E1 costs a session with a correctly-versioned plugin, while these 4.8 KB cost nothing. The conclusions live in the merged research doc; the **evidence** lives here. Those are not the same thing.

Positive controls are visible in every file (`CLAUDE.md` and `.claude/rules/general.md` at `session_start`; `.claude/rules/documentation.md` and `.claude/rules/safety.md` at `path_glob_match`), which is what makes the negative trustworthy rather than a silent instrument failure.

## Companion finding — plugin install state disturbs a live session's registry

Recorded here because it is the reason these logs exist in the shape they do, and because it is the same class as E1's main finding one layer up.

Getting a trustworthy E1 required uninstalling and reinstalling the flow plugin mid-session, to get off a **stale cached v1.29.0** — a pre-Phase-00 build with a dead `rules/` directory and zero `paths:` skills, which would have confounded the result. That reinstall silently broke **that session's own** skill and agent registry: `/flow:ship-spike` stopped resolving there, and the flow subagents dropped out, while fresh sessions still saw all 21 skills and 10 agents. **Nothing announced the change.** It surfaced only when a `Skill()` call failed — which is why the spike's ship ran in a spawned session with a handoff rather than in the research session.

The generalization: *what is registered is not always what is running*, and a session's view of its own plugin surface can go stale under it with no signal.

**Already captured durably** — not orphaned here. See `dev-docs/history.md` (the #144 entry's Lessons learned) and `dev-docs/roadmap.md`; the merged research doc references it too. This section is a cross-reference, not the system of record.

## Reproducing

```sh
# .claude/settings.local.json (gitignored)
{ "hooks": { "InstructionsLoaded": [ { "hooks": [
  { "type": "command", "command": "cat >> /tmp/loads.jsonl" } ] } ] } }
```

Then start a **fresh** session (the hook registers at session start), Read a file matching the glob under test, and inspect the log. Confirm the installed plugin version first — `claude plugin details flow@flow` — because a stale cache silently invalidates the result.
