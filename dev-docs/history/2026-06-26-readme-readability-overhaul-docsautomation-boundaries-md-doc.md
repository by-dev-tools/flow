### README readability overhaul + `docs/automation-boundaries.md` (docs-only, no version bump)
**Date:** 2026-06-26
**Branch:** `claude/great-kepler-920b8c` (PR pending; squash SHA at merge)
**Commit:** [range on branch; squash SHA filled at merge]

**What was done:**
Rewrote the public `README.md` to work as a portfolio-grade artifact (the user develops flow partly as a job-seeking/networking showcase of product thinking and taste — FB-0057). Cut from 227 → ~105 lines.
- **Re-sequenced to inverted-pyramid:** plain-language hero (value first) → the loop → what the reviewers catch → feedback loop → setup → under the hood → auxiliary skills (`doctor`, `workflow-help`, `ship-spike`, `log-disagreement`) moved to the bottom.
- **Collapsed two redundant loop tables into one skill-forward table.** The old README listed the 11 phases in one table and the skills-in-order in a second — the same sequence twice. The merged table makes skills the visible spine (indented `↳`) while keeping the non-skill anchors that carry the thesis: the two human gates and Execute.
- **Stripped version stamps + `FB-XXXX` refs from public prose.** The old header read `What v1.9.1 ships` while the plugin was at `v1.10.0` — a fan-out staleness cost of version-stamping marketing copy.
- **Preserved the cut detail** (AUTO/BOTH/AUTO·when-ready modes, full cold-start reality, soft-enforcement seams, known-limitations list, lineage) in a new linked `docs/automation-boundaries.md` rather than deleting it.

**Why:** The README communicated like an internal engineering reference — dense, defensive (a large cold-start `⚠️` wall near the top), version-stamped, with the most technical content first. For a reader landing cold (hiring managers, engineers, designers), value and the skill sequence weren't legible in the first screen.

**Design decisions:**
- *Skill-forward table, not skills-only list.* The user proposed presenting "just the skills as the phases." Pushed back: both gates and Execute are NOT skills, and the two-gate structure is the product's core claim — a skills-only list would erase it. Kept skills as the spine but retained the gates/Execute as bold non-skill rows. (FB-0057.)
- *Direct, plain copy.* A sample hero ("turns Claude Code into a disciplined teammate, not an eager intern") was rejected as performative/AI-sounding; rewrote with no metaphors or "not-X-but-Y". Saved as harness-memory `feedback_direct_no_fluff_copy` + FB-0057.
- *Table over SVG diagram for the loop.* Offered an SVG loop diagram vs a markdown table; user chose table-only (renders identically everywhere, zero asset maintenance, no GitHub inline-SVG sanitization issue).

**Technical decisions:** Docs-only change to repo-root `README.md` + a new `docs/` file — no plugin artifact (`plugins/flow/*`), schema, or skill behavior touched. No `plugin.json` version bump: the plugin's functional version is unchanged, so `roadmap.md` "Now" + `plan.md` "Current Focus" already reference `v1.10.0` and the ship doc-currency gate passes as-is.

**Tradeoffs discussed:**
- *Heavy cut vs completeness.* ~50% of the README was removed. Mitigated by routing the genuinely-useful detail to `docs/automation-boundaries.md` (linked twice) rather than dropping it — the honesty/limitations signal stays available one click away.
- *Re-running staff-review on a copy change.* The copy was reviewed interactively with the user across several iterations with explicit approval, so a separate four-lens `/flow:staff-review` pass was not spawned; recorded honestly in the PR `## Flow run` table rather than claimed.
