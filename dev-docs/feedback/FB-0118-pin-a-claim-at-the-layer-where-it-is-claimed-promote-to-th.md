# FB-0118 — "Pin a claim at the layer where it is claimed" is dev-side only; the shipped consumer rule-skill doesn't carry it

- **Date:** 2026-09-26
- **Source type:** hand-harvest of the lesson-harvest queue — the automated drain (`/flow:contribute`)
  was unrunnable in this repo (`flowRepoPath` unset), so this and four siblings were written up by hand
  rather than lost. See the meta-finding at the end of this entry and [[FB-0111]], its direct precedent.

- **What was said:** `.claude/rules/general.md` § Consistency discipline, item 4's corollary — **"pin a
  claim at the layer where it is CLAIMED, not the layer where it is implemented"** — landed on `main`
  as a dev-side rule for building flow. The rule is not flow-specific: it applies to any project where a
  criterion can be verified one layer below the surface it describes (an engine unit test green while
  the composed shell path it's wired into is broken). But `plugins/flow/skills/general/SKILL.md` — the
  shipped, project-agnostic rule-skill every flow **consumer** loads — has no "Consistency discipline"
  section at all. Verified 2026-09-26: `grep -c "Consistency" plugins/flow/skills/general/SKILL.md`
  returns 0; the file's five sections are Workflow discipline, Mode flags, Scope discipline, Decision
  tracking, Autonomous work guardrails.

- **Synthesized rule:** a lesson learned while building flow, and generalizable to any project (not
  specific to flow's own repo layout, doc paths, or ship pipeline), belongs in **both** the dev-side rule
  it was written into first **and** the shipped consumer rule-skill — the same split `.claude/rules/
  general.md`'s own header already states for three other sections (Scope discipline, Decision tracking,
  Autonomous work guardrails: "re-synced to the plugin's wording"). Consistency discipline items 1-4 were
  never added to that sync list, so they drifted the same way the header itself warns against for
  everything else in the file.

- **Candidate promotion (not implemented here — separate PR, separate review shape):** add a
  "Consistency discipline" section to `plugins/flow/skills/general/SKILL.md`, generalized the same way
  `.claude/rules/general.md`'s header instructs for the three already-synced sections (project-agnostic
  wording, no flow-specific file paths or FB citations in the shipped copy). At minimum item 3
  ("prohibition satisfiable by deletion") and item 4 ("a measurement that can only return clean is not a
  measurement," plus its "pin a claim at the layer where it is claimed" corollary) are the two most
  reusable — item 1 and item 2 are closer to flow's own doc-fragmentation and slot-fan-out specifics.

- **Applies to:** `plugins/flow/skills/general/SKILL.md`, `.claude/rules/general.md` (source of truth
  for the sync).
