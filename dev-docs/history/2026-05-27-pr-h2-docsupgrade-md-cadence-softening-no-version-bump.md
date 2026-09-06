### PR H2 — docs/upgrade.md cadence softening (no version bump)
**Date:** 2026-05-27
**Branch:** `pr-h2/upgrade-cadence-softening`
**Commit:** [SHA at ship time]

**What was done:**
Three copy edits to `docs/upgrade.md` after user feedback that the original PR-H1 prescription was too aggressive ("do I really need to run this after every session? every update? or just major updates?"):

1. **"When to run it" table rewritten** with semver-aware guidance. Old table had 5 triggers, all variations of "run the ritual." New table differentiates major/minor/patch bumps explicitly: major requires before-next-session; minor before-next-session in projects using the new surface; **patch is OPTIONAL — batch them, flow's discipline is additive at patch level so deferring is safe.** Added explicit "Mid-session: skip" and "Just to be safe: skip" rows. Plus a TL;DR at the top: "run when you want a specific new feature; otherwise weekly-ish hygiene is enough."

2. **"Multi-project ritual" → "Multi-project: once per machine (for user-scope installs)".** Original section claimed the ritual must run "in each project's Claude Code session" because the catalog cache is "per-session." That was wrong: for user-scope installs (the default), the catalog cache + the installed plugin both live at user-scope; one ritual run propagates to all projects on the machine. Project-scope installs (custom workflow) are the per-project case, but most consumers don't set that up. Section now distinguishes the two with a quick `jq` check for which scope you're in (with fail-loud fallback for jq-missing case, mirroring the existing FB-0009 pattern elsewhere in the same doc).

3. **Auto-update tradeoff hardened.** Old text said "for patch bumps, this is usually fine — flow's discipline is additive-only at patch level." That overpromised the additive guarantee. New text: "flow aims to be additive-only [at patch level]... the discipline is enforced by author care + lens-staff-engineer + /flow:doctor Check 2.5 — it's not a hard guarantee, so verify each upgrade with /flow:doctor regardless." Plus version-aware recommendation reframed as a principle: "when a major bump ships (any x.0.0), default to auto-update off until you've read the major-bump CHANGELOG; flip back on after you've understood the breaking changes." Rule propagates forward without naming a specific version.

**Why:**
User asked the cadence question directly. Re-reading my own upgrade.md surfaced that I'd overprescribed — every trigger row said "run the ritual" with no patch-vs-major distinction. A consumer following the prior table literally would have been running the 2-command ritual after every flow PR merge, even for trivial patch bumps. That's friction with no proportional benefit. The fix is copy-only; no behavior changes.

**Design decisions:**
- **No version bump.** Same precedent as PR H1: `docs/` lives at repo root, not inside `plugins/flow/`; consumers fetch the new copy from GitHub directly, not via `/plugin install`. No new behavior shipped.
- **Patch-bump = optional, not "skip entirely."** Considered telling consumers to never run the ritual for patch bumps unless they see a feature they want. Decided against: weekly-ish hygiene catches accumulated drift, and the cost of running the ritual is ~30 seconds. The current copy ("optional. Batch them") frames the right cadence without being absolute.
- **The "per-machine vs per-project" correction is a factual fix, not a softening.** The original "per-session" claim was wrong; I traced it from my Claude Code research and may have misread the source. The corrected description matches actual Claude Code marketplace + plugin-install behavior (per-machine for user-scope installs).
- **Auto-update recommendation reframed as a principle, not a named version.** Original "OFF starting v2.0.0" — named-version signaling — is fragile (no event surfaces it when v2.0.0 ships). New "when a major bump ships (any x.0.0), default off until you've read the CHANGELOG" propagates forward as a rule.

**Tradeoffs discussed:**
- **Where to surface "cadence" in the doc.** Considered (a) new section at top, (b) integrated into "When to run it" table, (c) rewriting both. Chose (b) + (c): the table itself carries the major/minor/patch distinction, with a TL;DR sentence above the table. Avoids creating a new section that competes with the existing structure.
- **Multi-project section accuracy.** The original "per-session" claim was a real factual error. Considered framing the fix as "clarification" — landed on "correction" instead per the .claude/rules/general.md scope discipline ("'why' goes in the documentation").

**Lessons learned:**
- **Docs overprescription is a real risk** when the author is also the maintainer dogfooding. The author internalizes "do this often" as a default and bakes it into the consumer-facing doc, where it reads as required cadence to someone less invested. The corrective surface is consumer feedback at first-read; this PR turns one such feedback round into a doc-shape change.
- **Per-session vs per-machine vs per-project install scoping.** Worth understanding deeply before writing install/upgrade docs. The original wrongness in PR H1 was caught only by an explicit user question. Routed as numbered plan FOLLOW-UP #27: `/flow:doctor` install-scope detection check would prevent future doc errors of this shape.
- **Parallel-PR collision via PR J (v1.2.5 adversarial sharpening, separate session).** While PR H2 was in flight, PR J shipped to main bumping the plugin to v1.2.5. Rebased PR H2 onto the new main + reconciled the v1.2.4-current → v1.2.5-current framing in plan.md Current Focus. The FB-0008 stale-base preflight gate would have caught this at /flow:ship time; manual rebase served the same role since this PR went via `gh pr create` after the workflow-loop completed (per PR I workflow-spawn discipline, /flow:ship should orchestrate end-to-end — captured as discipline reinforcement, not a new FOLLOW-UP).
