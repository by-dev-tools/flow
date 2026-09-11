### PR DC — Doc-currency in the ship pipeline — SAFETY
**Date:** 2026-06-05
**Branch:** `claude/doc-currency-pipeline`
**Commit:** (this PR; squash SHA at merge)

**What was done:**
Made the ship pipeline keep the forward-looking docs current automatically. `/flow:ship` gained **Step 5a** (doc-currency reconciliation — every ship refreshes roadmap "Now" with the current version + a "Recently shipped" line + a ▶ Next-up pointer, sweeps shipped plan items → "Recently Completed", and clears shipped `FB-XXXX` reservations) and **Step 5b** (a mechanical currency gate that asserts the manifest version appears in roadmap "Now" + plan "Current Focus", `exit 1` + reconcile-instruction on drift). The dev-side `.claude/skills/ship` got the same mirror; `/flow:doctor` got a *secondary* Check 2.6 of the same assertion; `workflow.md` Step 10 narrates the discipline. `docs/upgrade.md` was corrected (the "2-command ritual" was stale — `/plugin marketplace update` updates the installed plugin in one step; the doc now leads with `autoUpdate`). Dogfooded in this PR: the live staleness was fixed (roadmap "Now" read "v1.2.6"; plan "Current Focus" "v1.3.0" — both → v1.5.2). `SAFETY`: ship pipeline + install-surface manifests changed; the new gate is fail-fast (strengthens, never downgrades, error handling). v1.5.1 → v1.5.2.

**Why:**
Stale forward-looking docs are the FB-0010 fan-out class applied to *direction*. A cold reader — a new contributor, or the autonomous loop, which is a cold agent on every run — reads roadmap "Now"/plan "Current Focus" to decide what to do next. They had drifted ~5 versions because ship Step 5 wrote a backward-looking *history* entry + routed follow-ups, but nothing reconciled the forward-looking narrative or enforced currency. "Stale docs should never happen" (user direction, FB-0043).

**Design decisions:**
- **Enforcement in the pipeline (automatic), not in `/flow:doctor` (manual).** The user explicitly corrected an earlier draft that put the check only in doctor: "isn't doctor only run manually? I don't want to have to invoke this manually." So 5b runs on every ship; doctor's Check 2.6 is a *secondary* mirror for spotting drift between ships, never the enforcement.
- **Fail-and-reconcile, not auto-edit (user chose option a).** Step 5a (prompt, with judgment) does the doc edits; Step 5b (mechanical) only *verifies* they landed. Keeps the regex layer from rewriting prose.
- **Mechanical gate checks the version token only.** A version-string mismatch is the cheap, unambiguous signal that catches the worst drift; narrative correctness (the Recently-shipped list, the ▶ Next-up prose) stays the judgment of 5a — mechanizing prose-correctness is brittle and low-value.

**Technical decisions:**
- **Project-agnostic version source with graceful skip.** The gate resolves the version from `plugins/flow/.claude-plugin/plugin.json` → `.claude-plugin/plugin.json` → root `package.json`, and skips the mechanical check (keeping 5a) when none exists — so consumer projects without a versioned manifest aren't false-failed. No new schema slot.
- **Section-scoped grep with top-of-doc fallback** (`awk` extracts the "## Now" / "## Current Focus" section; falls back to `head -40` if the heading differs) so the check is precise on flow's convention and lenient elsewhere.

**Tradeoffs discussed:**
- Bundling the `docs/upgrade.md` fix (the originating thread) into the currency PR vs. splitting it (plan-critic Finding 2 raised scope). Kept bundled — it's the same *stale-doc* class, and the user requested the pipeline fix directly the prior turn (the "scope drift" finding was a false positive from cross-turn-context windowing).
- Mechanical narrative-currency (is "PR Q in flight" still true?) was considered and declined as too fuzzy; left to 5a's judgment.

**Lessons learned:**
- **The PR enforces its own thesis.** 5b ties the docs to the version bump: bumping `plugin.json` to 1.5.2 only passes once roadmap/plan say v1.5.2 — so a forgotten doc update blocks the ship. The currency fix can't itself ship stale.
- **The install confusion was itself a stale doc.** My earlier "two commands / reinstall" framing came from flow's own stale `upgrade.md`; verifying against `code.claude.com` (via the claude-code-guide agent) showed one command suffices. Fixed here — a fitting bug for a doc-currency PR.
- **Stale docs were not a one-off.** roadmap "Now" (v1.2.6), plan "Current Focus" (v1.3.0), and 17 lines of merged-PR Handoff Notes had all rotted — confirming this needed a mechanical fix, not another manual cleanup.
