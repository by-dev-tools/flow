### Route two post-V3b follow-ups from the health-tracker cold-run pre-check (docs-only)
**Date:** 2026-06-16
**Branch:** claude/v3b-followups
**Commit:** [this PR]

**What was done:**
Captured two findings surfaced while prepping the FB-0016 health-tracker (iOS) cold-run that validates V3b's §5c distill step, as `dev-docs/roadmap.md` entries: (1) a roadmap-concrete item in the "V3b durable-record follow-ups" bundle — `insert-visual-history.py` keys on the skeleton's marker comments, so a consumer pointing `visualHistoryPath` at a *pre-existing, hand-authored* `visual-history.html` (health-tracker's `craft/visual-history.html`, the #10 reference) gets a fail-loud, not an adoption; they must use a fresh path. (2) a § Exploration entry — installed-plugin-version currency: the pre-check found the user-level flow install cached at v1.5.1 while `main` was v1.8.0, so a ship would run stale prose until `/plugin marketplace update`; nothing surfaces "your install is behind `main`."

**Why:**
The cold-run pre-check is the first time V3b met a real consumer's filesystem. Both findings are real friction a future session will hit; routing them to the roadmap (not just a chat message) is the canonical capture per the workflow's follow-up discipline.

**Design decisions:**
- The markerless-adoption finding is roadmap-concrete (it has a shape: `--migrate` mode / clearer diagnostic / document-the-constraint), so it lives in the V3b follow-ups bundle, not § Exploration.
- The version-currency finding has no clean shape yet (needs a "latest" reference + a non-annoying cadence; `autoUpdate` is the blunt alternative), so it's § Exploration with a `Surfaces when:` trigger on `/flow:doctor` / `docs/upgrade.md`.

**Tradeoffs discussed:**
- Live-confirmed the install-lag this session: even after the user updated the cache to 1.8.0, the running session's skill resolution stayed pinned to 1.5.1 (picks up 1.8.0 on restart) — so the validation cold-run must verify the installed version FIRST, which the health-tracker prompt now does. No code change here — pure routing so the findings aren't lost.
