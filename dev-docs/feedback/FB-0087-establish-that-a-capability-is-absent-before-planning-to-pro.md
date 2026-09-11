### FB-0087 — Establish that a capability is absent before planning to provide it; the platform may already ship it

**Date:** 2026-08-23
**Source type:** user correction

**What was said.** A staged orchestrator proposal included a "Phase 2" whose job was a `.conductor/settings.toml` setup script, so every spawned cloud workspace would bootstrap the flow plugin identically. The user cut it: *"how necessary is phase 2 given the conductor cloud computer setup? flow will always be installed because of the nature of the setup."* Checking rather than arguing settled it in one command — `~/.claude/plugins/installed_plugins.json` records flow at **user** scope with `installedAt 2026-08-19T04:51`, while the workspace it was running in was created `2026-08-20T21:40`. The plugin *predates the workspace*, so it comes from the cloud-computer image and is present in every new workspace by construction. The phase was solving a problem the platform had already solved.

**Synthesized rule.** Before planning work whose purpose is to *provide* a capability, spend one command establishing that the capability is actually absent. A proposal that adds a bootstrap / setup / sync layer is **asserting an absence**, and that assertion is a load-bearing claim that belongs in the plan's confidence verdicts — verified before the phase is scoped, not after it is built. The cost of getting it wrong is not the wasted plan (plans are cheap); it is that scaffolding built over a capability the platform already supplies becomes permanent maintenance with no corresponding benefit, and it is invisible from then on precisely *because it works*.

**Corollary — what survives the cut is usually narrower and genuinely load-bearing.** Here the image pins a *version*: `known_marketplaces.lastUpdated` had not moved in days and the installed plugin was already a commit behind `origin/main`. So the residue is a **version assertion**, not an install step — a much smaller artifact than the phase it replaced.

**Applies to:** planning discipline (`plugins/flow/docs/workflow.md` Step 2 confidence verdicts) and any staged plan that opens with an environment-bootstrap phase. Related: FB-0085 (verify a mechanism against the runtime, not its own documentation — the same discipline one layer up: verify the *environment* against the runtime, not against your model of it), FB-0088 (the bloat this avoids), FB-0010.
