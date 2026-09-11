### Concise external overview doc (`docs/how-it-works.md`)
**Date:** 2026-07-01
**Branch:** claude/angry-wozniak-08892e

**What was done:**
Added `docs/how-it-works.md` — a one-minute, external-audience explanation of the flow loop, structured as a bulleted walk through the loop (plan → critique → approve → build → review → run-it-for-real → visual walkthrough → PR + skip audit → merge) plus a one-line net-effect close. Added a "In a hurry?" pointer to it near the top of `README.md`.

**Why:**
The README is thorough but long. There was no short surface to hand someone (e.g. a Discord/DM share) who wants to understand how flow works and what's distinct about it without reading the full doc. This fills the gap between the one-line tagline and the full README/`workflow.md`.

**Design decisions:**
- **Neutral/second-person voice, not first-person.** The source draft was a first-person "how I run flow" pitch; a checked-in repo doc is read by anyone, so "you approve / you merge" reads correctly where "I" would not.
- **De-jargoned deliberately.** Terms that don't stand alone to an outsider (e.g. the "push further" review lens) are described by what they do, not named. The behavioral gate is spelled out concretely — it launches the real app in a browser (Playwright) or simulator (Xcode/Android), drives it via MCP, and screenshots each state — so readers grasp what "verify" actually means.
- **Kept the bulleted loop as the centerpiece** (the most-requested element during drafting) and folded the "what's unique" points into the relevant bullets rather than a separate section.

**Tradeoffs discussed:**
- Overview doc vs. trimming the README: chose an additive short doc so the README stays the complete reference and the short doc stays skimmable, linked both ways.

**Lessons learned:**
- Reinforces the existing "direct, no-fluff copy" preference (memory: `feedback_direct_no_fluff_copy`): concrete mechanics beat abstract claims for an external reader.
