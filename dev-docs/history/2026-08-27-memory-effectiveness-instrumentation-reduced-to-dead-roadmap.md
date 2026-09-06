## 2026-08-27 — Memory-effectiveness instrumentation, reduced to `--dead` (roadmap #3, FB-0094)

**Branch:** `conductor/3-memory-effectiveness-instrumentation` · **PR:** #(assigned at open) · **Mode:** feature

**What was done.** `tools/memory/check.mjs` gains `--dead [--days=N]` (default 60), which
mechanically lists failure-pattern memory entries with no activity — most recent `Fire log`
date, falling back to `First seen`, falling back to file mtime — older than the threshold.
`/flow:ship` § 4b.vi (and the mirrored `ship-spike` bullet) now run it before spawning the
periodic-audit Explore agent and feed its output in as a deterministic candidate list, instead
of leaving the agent to compute date arithmetic across up to 30 entries by hand. New eval
harness `run_memory_check_evals.py` (fixture-driven, subprocess against the real script, no
mocking) wired into `ci.yml`.

**Why.** `dev-docs/roadmap.md` § Next "#3" named three pieces: (a) fire-count instrumentation,
(b) dead-entry surfacing, (c) fire-rate×recency ranking of "injection." Flow's memory corpus is
count-capped (30) + mtime-sorted with a purely manual, eyeballed audit for staleness — nothing
mechanized any of it.

**Design decisions.**
- **Scope cut to (b) only, mid-plan, by the human.** The initial plan (all three pieces) was
  critiqued via `/flow:critique-plan`, fixed, and presented — but its own analysis had already
  surfaced the ceiling: flow's `check.mjs` only *reports on* `~/.claude/projects/<canonical>/
  memory/`; the harness's native auto-memory loader reads that directory directly, and flow has
  no index file or injection-order hook. So (c) could only ever reorder a curation-facing
  `--list` output over a corpus capped at 30 files — real machinery (a scoring formula, a
  deterministic `--record-fire` writer to keep it robust, a pinned Fire-log write syntax) for a
  cosmetic payoff. The human's direction: "you found the ceiling yourself... `--dead` is the
  one piece with a genuine consumer." Synthesized as FB-0094. Full original-scope plan and the
  cut rationale are preserved in the "PR — Memory-effectiveness instrumentation" block in
  `plan.md`.
- **Two corrections to the original dispatch brief**, made before scoping: `tools/memory/
  check.mjs` doesn't exist at that path — the real file is `plugins/flow/tools/memory/
  check.mjs`, a **shipped plugin artifact** (used by `/flow:ship`, `/flow:ship-spike`,
  `/flow:post-merge`), not a `tools/model-measure/`-style dev tool. All work stayed inside
  `plugins/flow/` accordingly, under the "prompt changes are code changes" bar (eval fixture
  required).
- **Calendar-days (60), not "N ships," for the dead-entry threshold.** The roadmap literally
  said "no fire in N ships," but that requires a new per-entry, per-ship counter (incremented
  on every ship run for every non-firing entry) with no existing analog. Calendar-days reuses
  timestamps already captured in the `Fire log`/`First seen` bullets and mechanizes wording
  `/flow:ship` § 4b.vi's prose already committed to ("no activity in 60+ days"). Recommended at
  medium confidence, accepted by the human unchanged when the ranking-formula question (the
  other open decision) went moot with the cut.
- **Lenient date extraction, not a pinned write format.** Since `--record-fire` was cut, the
  parser has no deterministic writer to depend on — it still has to read whatever the existing
  freehand `ship § 4b.v` append produces. `extractDates`/`fieldLine` regex-scan for any
  `YYYY-MM-DD` substring after a `**Fire log**`/`**First seen**` bullet rather than assuming one
  exact separator style, so pre-existing entries and future freehand appends both parse.
- **Three-tier `lastActivity` fallback** (last fire → first seen → file mtime), each tier only
  reached if the one before is unparseable — never throws on a pre-this-feature entry with no
  `Fire log` bullet at all (the malformed-input path the quality bar requires).

**Technical decisions.**
- `--list`, `--count`, `--audit-due`, and the default summary are byte-for-byte unchanged —
  `--dead` is a pure addition, confirmed by the eval's regression cases.
- The eval harness builds its fixture memory dir under a real `~/.claude/projects/` tempdir
  (required by `check.mjs`'s own `validateMemoryDir` path guard — nothing outside that root is
  accepted) and saves/restores the shared `.last-audit` marker (which lives beside the script,
  per-install rather than per-fixture-dir) around its one `--audit-due` regression check, so the
  eval run doesn't perturb real ship-counter state.
- No new `flow.config.json` schema slot for the day threshold — hardcoded `DEAD_ENTRY_DAYS = 60`
  constant, mirroring the existing unconfigurable `AUDIT_INTERVAL = 5`. Avoids a slot-count
  fan-out (`workflow.md`'s "33 slots" line, the schema's 40 property keys) for a threshold that's
  a one-line change if it ever needs tuning.

**Tradeoffs discussed.** Building the full three-piece plan would have delivered a "correct in
principle" ranking system whose only real effect was reordering a report nobody but a human
curating a 30-entry corpus reads — cost (scoring formula, deterministic writer, a newly-pinned
markdown field contract, more eval surface) clearly outweighing payoff once the injection-control
ceiling was named explicitly. Calendar-days over ship-count trades literal roadmap-wording fidelity
for zero new bookkeeping; accepted as the right trade since ship-count doesn't obviously behave
better across projects with different ship cadences either.

**`/simplify` (4-lens pass) caught one real correctness bug and two minor cleanups, all fixed
in-tree.** The altitude lens found that `fieldLine` (the helper reading a `**Fire log**`/`**First
seen**` bullet) matched only the *first* line containing the label — so if a repeated firing were
appended as its own new bullet line rather than onto the existing line (a shape nothing pins;
`--record-fire`, which would have made the write format moot, was the piece that got cut), later
fires would be silently dropped and an actively-firing entry could read as dead. Its own comment
claimed a "one-bullet-per-field" contract that doesn't actually exist in `rules/documentation.md`
or `ship/SKILL.md` § 4b.v. Fixed by unioning dates across every matching line (`fieldLine` →
`fieldLines`, `'g'`-flagged) rather than pinning the write format — consistent with the parser's
stated design goal of tolerating freehand appends. Added a fixture
(`feedback_split_fire_lines.md`) writing fires across two separate bullet lines to pin the fix;
without it the bug was invisible to CI (the original fixture always comma-joined fire dates onto
one line). The simplification lens also found `parseEntry`'s `firstSeen` field was computed for
internal fallback use but returned and never read by any caller (dead output once the
fire-rate-ranking consumer was cut) — dropped from the return shape — and that `daysSince` was
computed twice per stale entry (once to filter, once to print) — now computed once and threaded
through. The eval's 7 near-identical `--dead`-default presence/absence checks collapsed into one
data-driven table. Reuse and efficiency lenses returned clean.

**`/flow:staff-review` (4 lenses) caught one real correctness bug and three cheap-nit
improvements, all fixed in-tree; two lenses N/A'd correctly.** Design-engineer lens: no visual
surface in this diff (confirmed by inspection, not assumed) — correctly returned no findings.
Staff-engineer lens found the more serious issue: `fieldLines`' regex still matched
`**Fire log**` (or `**First seen**`) **anywhere in a line**, not just on the bullet line itself —
so a *different* field's prose (e.g. a `Pattern` field discussing the feature and happening to
bold "**Fire log**") could have its own nearby dates misread as real activity, silently making a
genuinely-stale entry look fresh and defeating `--dead`'s entire purpose. Fixed by anchoring the
regex to the bullet marker (`^\s*-\s*\*\*Label\*\*.*$`, multiline). Added
`feedback_prose_mentions_fire_log.md` (a real 90-day-old fire, with Pattern-field prose bolding
"Fire log"/"First seen" near recent dates that must not count) to pin it, and confirmed the fix
is load-bearing by temporarily reverting the regex and re-running the harness (red: 1 failure on
that exact fixture; green after restoring the fix). UX-designer + staff-engineer lenses
independently converged on the same `--days=` validation gap: `parseInt` accepts fractional
(`30.5`→30) and the original regex silently skipped an empty value (`--days=` with nothing after
`=`), so both bypassed the PR's own "loud warning, never a silent wrong-default" contract (the
Spec-walk's own words). Fixed by validating the raw string (`/^\d+$/`) before `parseInt` rather
than checking `Number.isInteger` after it. UX-designer also found that passing `--days=` twice
could set a value from the first flag, then print a warning about a *different*, second flag —
message and behavior disagreeing. Fixed by honoring only the first `--days=` occurrence
(valid or not) and never inspecting a second one, so the message always describes what's actually
in effect; and that `--dead`'s printed line carried only a relative day-count while `--list`
prints an absolute ISO date, forcing a reader to compute the date themselves. Push-further lens
(independently) found the same shape from a different angle: the day-count alone can't
distinguish "known-quiet since a real date" from "no dates recorded at all, mtime is just
noise" — the exact ambiguity `parseEntry`'s three-tier fallback exists to resolve, thrown away
before printing. Both close with one fix: `parseEntry` now returns `activitySource`
(`fire`/`first-seen`/`mtime`), and the `--dead` line prints the ISO date plus which tier resolved
it (e.g. `2026-XX-XX, 90d since last activity via fire, 1 fire`) — added a backdated-mtime
fixture (`feedback_stale_mtime_only.md`, via `os.utime`) since no prior fixture actually exercised
the `mtime` tier in the *stale* set. Staff-engineer's remaining findings were accepted as
documented, no-action tradeoffs: the mtime-fallback-resets-on-rehome case (now called out
explicitly in `parseEntry`'s comment), `DEAD_ENTRY_DAYS` as a second hardcoded constant matching
the `AUDIT_INTERVAL` precedent (already reasoned about in this entry's Technical decisions), and
the eval's dependency on a writable `~/.claude/projects/` (already documented in the harness's own
docstring) — plus a cosmetic `fieldLine`→`fieldLines` doc-drift fix in `plan.md`. Reviewer notes
kept in this history entry rather than a separate PR-body section since this is a LOCAL-ONLY
review (no PR existed yet) folded directly into the ship pipeline that opens one.

**Three-surface note.** Entirely inside `plugins/flow/` (shipped plugin artifact) plus this
`dev-docs/` entry and `.github/workflows/ci.yml`. No `.claude/`/`tools/` (project-dev infra)
touched.
